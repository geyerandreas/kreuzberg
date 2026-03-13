//! Core cache implementation with GenericCache struct.
//!
//! # Lock Poisoning Handling
//!
//! This module uses `Arc<Mutex<T>>` for thread-safe state management and implements
//! explicit lock poisoning recovery throughout all public methods:
//!
//! **What is lock poisoning?**
//! - When a thread panics while holding a Mutex, the lock becomes "poisoned"
//! - Rust marks the Mutex to indicate data may be in an inconsistent state
//! - Subsequent lock attempts return `Err(PoisonError)` instead of acquiring the lock
//!
//! **Recovery strategy:**
//! - All `.lock()` calls use `.map_err()` to convert `PoisonError` into `KreuzbergError::LockPoisoned`
//! - The error propagates to callers via `Result` returns (never `.unwrap()` on locks)
//! - Provides clear error messages indicating which mutex is poisoned
//! - Follows CLAUDE.md requirement: "Lock poisoning must be handled - never `.unwrap()` on Mutex/RwLock"
//!
//! **Affected state:**
//! - `processing_locks`: Tracks cache keys currently being processed (6 lock sites)
//! - `deleting_files`: Prevents read-during-delete race conditions (3 lock sites)
//!
//! This approach ensures that lock poisoning (rare in practice) is surfaced to users
//! rather than causing panics, maintaining system stability during concurrent operations.

use crate::error::{KreuzbergError, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use super::cleanup::smart_cleanup_cache;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub total_files: usize,
    pub total_size_mb: f64,
    pub available_space_mb: f64,
    pub oldest_file_age_days: f64,
    pub newest_file_age_days: f64,
}

#[derive(Debug, Clone)]
pub(super) struct CacheEntry {
    pub(super) path: PathBuf,
    pub(super) size: u64,
    pub(super) modified: SystemTime,
}

pub(super) struct CacheScanResult {
    pub(super) stats: CacheStats,
    pub(super) entries: Vec<CacheEntry>,
}

pub struct GenericCache {
    cache_dir: PathBuf,
    cache_type: String,
    max_age_days: f64,
    max_cache_size_mb: f64,
    min_free_space_mb: f64,
    processing_locks: Arc<Mutex<HashSet<String>>>,
    /// Tracks cache keys being deleted to prevent read-during-delete race conditions
    deleting_files: Arc<Mutex<HashSet<PathBuf>>>,
    /// Counter for triggering periodic cleanup (every 100 writes)
    write_counter: Arc<AtomicUsize>,
}

impl GenericCache {
    pub fn new(
        cache_type: String,
        cache_dir: Option<String>,
        max_age_days: f64,
        max_cache_size_mb: f64,
        min_free_space_mb: f64,
    ) -> Result<Self> {
        let cache_dir_path = if let Some(dir) = cache_dir {
            PathBuf::from(dir).join(&cache_type)
        } else if let Ok(env_path) = std::env::var("KREUZBERG_CACHE_DIR") {
            PathBuf::from(env_path).join(&cache_type)
        } else {
            std::env::current_dir()?.join(".kreuzberg").join(&cache_type)
        };

        fs::create_dir_all(&cache_dir_path)
            .map_err(|e| KreuzbergError::cache(format!("Failed to create cache directory: {}", e)))?;

        Ok(Self {
            cache_dir: cache_dir_path,
            cache_type,
            max_age_days,
            max_cache_size_mb,
            min_free_space_mb,
            processing_locks: Arc::new(Mutex::new(HashSet::new())),
            deleting_files: Arc::new(Mutex::new(HashSet::new())),
            write_counter: Arc::new(AtomicUsize::new(0)),
        })
    }

    fn get_cache_path(&self, cache_key: &str) -> PathBuf {
        self.cache_dir.join(format!("{}.msgpack", cache_key))
    }

    fn get_metadata_path(&self, cache_key: &str) -> PathBuf {
        self.cache_dir.join(format!("{}.meta", cache_key))
    }

    fn is_valid(&self, cache_path: &Path, source_file: Option<&str>) -> bool {
        if !cache_path.exists() {
            return false;
        }

        if let Ok(metadata) = fs::metadata(cache_path)
            && let Ok(modified) = metadata.modified()
            && let Ok(elapsed) = SystemTime::now().duration_since(modified)
        {
            let age_days = elapsed.as_secs() as f64 / (24.0 * 3600.0);
            if age_days > self.max_age_days {
                return false;
            }
        }

        if let Some(source_path) = source_file {
            let Some(file_stem) = cache_path.file_stem().and_then(|s| s.to_str()) else {
                return false;
            };
            let meta_path = self.get_metadata_path(file_stem);

            if meta_path.exists() {
                if let Ok(meta_metadata) = fs::metadata(&meta_path)
                    && meta_metadata.len() == 16
                    && let Ok(cached_meta_bytes) = fs::read(&meta_path)
                {
                    let cached_size = u64::from_le_bytes([
                        cached_meta_bytes[0],
                        cached_meta_bytes[1],
                        cached_meta_bytes[2],
                        cached_meta_bytes[3],
                        cached_meta_bytes[4],
                        cached_meta_bytes[5],
                        cached_meta_bytes[6],
                        cached_meta_bytes[7],
                    ]);
                    let cached_mtime = u64::from_le_bytes([
                        cached_meta_bytes[8],
                        cached_meta_bytes[9],
                        cached_meta_bytes[10],
                        cached_meta_bytes[11],
                        cached_meta_bytes[12],
                        cached_meta_bytes[13],
                        cached_meta_bytes[14],
                        cached_meta_bytes[15],
                    ]);

                    if let Ok(source_metadata) = fs::metadata(source_path) {
                        let current_size = source_metadata.len();
                        let Some(current_mtime) = source_metadata
                            .modified()
                            .ok()
                            .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                            .map(|d| d.as_secs())
                        else {
                            return false;
                        };

                        return cached_size == current_size && cached_mtime == current_mtime;
                    }
                }
                return false;
            }
        }

        true
    }

    fn save_metadata(&self, cache_key: &str, source_file: Option<&str>) {
        if let Some(source_path) = source_file
            && let Ok(metadata) = fs::metadata(source_path)
        {
            let size = metadata.len();
            let Some(mtime) = metadata
                .modified()
                .ok()
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_secs())
            else {
                return;
            };

            let mut bytes = Vec::with_capacity(16);
            bytes.extend_from_slice(&size.to_le_bytes());
            bytes.extend_from_slice(&mtime.to_le_bytes());

            let meta_path = self.get_metadata_path(cache_key);
            // Cache metadata write failure - safe to ignore, cache is optional fallback ~keep
            let _ = fs::write(meta_path, bytes);
        }
    }

    #[cfg_attr(feature = "otel", tracing::instrument(
        skip(self),
        fields(
            cache.hit = tracing::field::Empty,
            cache.key = %cache_key,
        )
    ))]
    pub fn get(&self, cache_key: &str, source_file: Option<&str>) -> Result<Option<Vec<u8>>> {
        let cache_path = self.get_cache_path(cache_key);

        {
            let deleting = self
                .deleting_files
                .lock()
                .map_err(|e| KreuzbergError::LockPoisoned(format!("Deleting files mutex poisoned: {}", e)))?;
            if deleting.contains(&cache_path) {
                #[cfg(feature = "otel")]
                tracing::Span::current().record("cache.hit", false);
                return Ok(None);
            }
        }

        if !self.is_valid(&cache_path, source_file) {
            #[cfg(feature = "otel")]
            tracing::Span::current().record("cache.hit", false);
            return Ok(None);
        }

        match fs::read(&cache_path) {
            Ok(content) => {
                #[cfg(feature = "otel")]
                tracing::Span::current().record("cache.hit", true);
                Ok(Some(content))
            }
            Err(_) => {
                // Best-effort cleanup of corrupted cache files ~keep
                if let Err(e) = fs::remove_file(&cache_path) {
                    tracing::debug!("Failed to remove corrupted cache file: {}", e);
                }
                if let Err(e) = fs::remove_file(self.get_metadata_path(cache_key)) {
                    tracing::debug!("Failed to remove corrupted metadata file: {}", e);
                }
                #[cfg(feature = "otel")]
                tracing::Span::current().record("cache.hit", false);
                Ok(None)
            }
        }
    }

    #[cfg_attr(feature = "otel", tracing::instrument(
        skip(self, data),
        fields(
            cache.key = %cache_key,
            cache.size_bytes = data.len(),
        )
    ))]
    pub fn set(&self, cache_key: &str, data: Vec<u8>, source_file: Option<&str>) -> Result<()> {
        let cache_path = self.get_cache_path(cache_key);

        fs::write(&cache_path, &data)
            .map_err(|e| KreuzbergError::cache(format!("Failed to write cache file: {}", e)))?;

        self.save_metadata(cache_key, source_file);

        let count = self.write_counter.fetch_add(1, Ordering::Relaxed);
        if count.is_multiple_of(100)
            && let Some(cache_path_str) = self.cache_dir.to_str()
        {
            // Cache cleanup failure - safe to ignore, cache is optional fallback ~keep
            let _ = smart_cleanup_cache(
                cache_path_str,
                self.max_age_days,
                self.max_cache_size_mb,
                self.min_free_space_mb,
            );
        }

        Ok(())
    }

    pub fn is_processing(&self, cache_key: &str) -> Result<bool> {
        // OSError/RuntimeError must bubble up - system errors need user reports ~keep
        let locks = self
            .processing_locks
            .lock()
            .map_err(|e| KreuzbergError::LockPoisoned(format!("Processing locks mutex poisoned: {}", e)))?;
        Ok(locks.contains(cache_key))
    }

    pub fn mark_processing(&self, cache_key: String) -> Result<()> {
        // OSError/RuntimeError must bubble up - system errors need user reports ~keep
        let mut locks = self
            .processing_locks
            .lock()
            .map_err(|e| KreuzbergError::LockPoisoned(format!("Processing locks mutex poisoned: {}", e)))?;
        locks.insert(cache_key);
        Ok(())
    }

    pub fn mark_complete(&self, cache_key: &str) -> Result<()> {
        // OSError/RuntimeError must bubble up - system errors need user reports ~keep
        let mut locks = self
            .processing_locks
            .lock()
            .map_err(|e| KreuzbergError::LockPoisoned(format!("Processing locks mutex poisoned: {}", e)))?;
        locks.remove(cache_key);
        Ok(())
    }

    /// Mark a file path as being deleted to prevent concurrent reads.
    ///
    /// # TOCTOU Race Condition
    ///
    /// There is a Time-Of-Check-To-Time-Of-Use (TOCTOU) race condition between:
    /// 1. Iterating directory entries in `clear()` (getting path/metadata)
    /// 2. Marking the file for deletion here
    /// 3. Actually deleting the file
    ///
    /// **Race scenario:**
    /// - Thread A: Begins iterating in `clear()`, gets path
    /// - Thread B: Calls `get()`, checks `deleting_files` (not marked yet), proceeds
    /// - Thread A: Calls `mark_for_deletion()` here
    /// - Thread A: Deletes file with `fs::remove_file()`
    /// - Thread B: Tries to read file, but it's already deleted
    ///
    /// **Why this is acceptable:**
    /// - Cache operations are best-effort optimizations, not critical
    /// - `get()` already handles file read failures gracefully (treats as cache miss)
    /// - The worst case is a failed read → cache miss → recomputation
    /// - No data corruption or invariant violations occur
    /// - Alternative (atomic operation) would require complex locking impacting performance
    fn mark_for_deletion(&self, path: &Path) -> Result<()> {
        let mut deleting = self
            .deleting_files
            .lock()
            .map_err(|e| KreuzbergError::LockPoisoned(format!("Deleting files mutex poisoned: {}", e)))?;
        deleting.insert(path.to_path_buf());
        Ok(())
    }

    /// Remove a file path from the deletion set
    fn unmark_deletion(&self, path: &Path) -> Result<()> {
        let mut deleting = self
            .deleting_files
            .lock()
            .map_err(|e| KreuzbergError::LockPoisoned(format!("Deleting files mutex poisoned: {}", e)))?;
        deleting.remove(&path.to_path_buf());
        Ok(())
    }

    pub fn clear(&self) -> Result<(usize, f64)> {
        let dir_path = &self.cache_dir;

        if !dir_path.exists() {
            return Ok((0, 0.0));
        }

        let mut removed_count = 0;
        let mut removed_size = 0.0;

        let read_dir = fs::read_dir(dir_path)
            .map_err(|e| KreuzbergError::cache(format!("Failed to read cache directory: {}", e)))?;

        for entry in read_dir {
            let entry = match entry {
                Ok(e) => e,
                Err(e) => {
                    tracing::debug!("Error reading entry: {}", e);
                    continue;
                }
            };

            let metadata = match entry.metadata() {
                Ok(m) if m.is_file() => m,
                _ => continue,
            };

            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) != Some("msgpack") {
                continue;
            }

            let size_mb = metadata.len() as f64 / (1024.0 * 1024.0);

            // Mark file for deletion to prevent concurrent access ~keep
            if let Err(e) = self.mark_for_deletion(&path) {
                tracing::debug!("Failed to mark file for deletion: {} (continuing anyway)", e);
            }

            match fs::remove_file(&path) {
                Ok(_) => {
                    removed_count += 1;
                    removed_size += size_mb;
                    // Unmark after successful deletion ~keep
                    if let Err(e) = self.unmark_deletion(&path) {
                        tracing::debug!("Failed to unmark deleted file: {} (non-critical)", e);
                    }
                }
                Err(e) => {
                    tracing::debug!("Failed to remove {:?}: {}", path, e);
                    // Unmark after failed deletion to allow retries ~keep
                    if let Err(e) = self.unmark_deletion(&path) {
                        tracing::debug!("Failed to unmark file after deletion error: {} (non-critical)", e);
                    }
                }
            }
        }

        Ok((removed_count, removed_size))
    }

    pub fn get_stats(&self) -> Result<CacheStats> {
        use super::cleanup::get_cache_metadata;
        let cache_path_str = self
            .cache_dir
            .to_str()
            .ok_or_else(|| KreuzbergError::validation("Cache directory path contains invalid UTF-8".to_string()))?;
        get_cache_metadata(cache_path_str)
    }

    pub fn cache_dir(&self) -> &Path {
        &self.cache_dir
    }

    pub fn cache_type(&self) -> &str {
        &self.cache_type
    }
}
