
let imports = {};
imports['__wbindgen_placeholder__'] = module.exports;

function addToExternrefTable0(obj) {
    const idx = wasm.__externref_table_alloc();
    wasm.__wbindgen_externrefs.set(idx, obj);
    return idx;
}

const CLOSURE_DTORS = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(state => state.dtor(state.a, state.b));

function debugString(val) {
    // primitive types
    const type = typeof val;
    if (type == 'number' || type == 'boolean' || val == null) {
        return  `${val}`;
    }
    if (type == 'string') {
        return `"${val}"`;
    }
    if (type == 'symbol') {
        const description = val.description;
        if (description == null) {
            return 'Symbol';
        } else {
            return `Symbol(${description})`;
        }
    }
    if (type == 'function') {
        const name = val.name;
        if (typeof name == 'string' && name.length > 0) {
            return `Function(${name})`;
        } else {
            return 'Function';
        }
    }
    // objects
    if (Array.isArray(val)) {
        const length = val.length;
        let debug = '[';
        if (length > 0) {
            debug += debugString(val[0]);
        }
        for(let i = 1; i < length; i++) {
            debug += ', ' + debugString(val[i]);
        }
        debug += ']';
        return debug;
    }
    // Test for built-in
    const builtInMatches = /\[object ([^\]]+)\]/.exec(toString.call(val));
    let className;
    if (builtInMatches && builtInMatches.length > 1) {
        className = builtInMatches[1];
    } else {
        // Failed to match the standard '[object ClassName]'
        return toString.call(val);
    }
    if (className == 'Object') {
        // we're a user defined class or Object
        // JSON.stringify avoids problems with cycles, and is generally much
        // easier than looping through ownProperties of `val`.
        try {
            return 'Object(' + JSON.stringify(val) + ')';
        } catch (_) {
            return 'Object';
        }
    }
    // errors
    if (val instanceof Error) {
        return `${val.name}: ${val.message}\n${val.stack}`;
    }
    // TODO we could test for more things here, like `Set`s and `Map`s.
    return className;
}

function getArrayU8FromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return getUint8ArrayMemory0().subarray(ptr / 1, ptr / 1 + len);
}

function getCachedStringFromWasm0(ptr, len) {
    if (ptr === 0) {
        return getFromExternrefTable0(len);
    } else {
        return getStringFromWasm0(ptr, len);
    }
}

let cachedDataViewMemory0 = null;
function getDataViewMemory0() {
    if (cachedDataViewMemory0 === null || cachedDataViewMemory0.buffer.detached === true || (cachedDataViewMemory0.buffer.detached === undefined && cachedDataViewMemory0.buffer !== wasm.memory.buffer)) {
        cachedDataViewMemory0 = new DataView(wasm.memory.buffer);
    }
    return cachedDataViewMemory0;
}

function getFromExternrefTable0(idx) { return wasm.__wbindgen_externrefs.get(idx); }

function getStringFromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return decodeText(ptr, len);
}

let cachedUint8ArrayMemory0 = null;
function getUint8ArrayMemory0() {
    if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
        cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
    }
    return cachedUint8ArrayMemory0;
}

function handleError(f, args) {
    try {
        return f.apply(this, args);
    } catch (e) {
        const idx = addToExternrefTable0(e);
        wasm.__wbindgen_exn_store(idx);
    }
}

function isLikeNone(x) {
    return x === undefined || x === null;
}

function makeMutClosure(arg0, arg1, dtor, f) {
    const state = { a: arg0, b: arg1, cnt: 1, dtor };
    const real = (...args) => {

        // First up with a closure we increment the internal reference
        // count. This ensures that the Rust closure environment won't
        // be deallocated while we're invoking it.
        state.cnt++;
        const a = state.a;
        state.a = 0;
        try {
            return f(a, state.b, ...args);
        } finally {
            state.a = a;
            real._wbg_cb_unref();
        }
    };
    real._wbg_cb_unref = () => {
        if (--state.cnt === 0) {
            state.dtor(state.a, state.b);
            state.a = 0;
            CLOSURE_DTORS.unregister(state);
        }
    };
    CLOSURE_DTORS.register(real, state, state);
    return real;
}

function passArrayJsValueToWasm0(array, malloc) {
    const ptr = malloc(array.length * 4, 4) >>> 0;
    for (let i = 0; i < array.length; i++) {
        const add = addToExternrefTable0(array[i]);
        getDataViewMemory0().setUint32(ptr + 4 * i, add, true);
    }
    WASM_VECTOR_LEN = array.length;
    return ptr;
}

function passStringToWasm0(arg, malloc, realloc) {
    if (realloc === undefined) {
        const buf = cachedTextEncoder.encode(arg);
        const ptr = malloc(buf.length, 1) >>> 0;
        getUint8ArrayMemory0().subarray(ptr, ptr + buf.length).set(buf);
        WASM_VECTOR_LEN = buf.length;
        return ptr;
    }

    let len = arg.length;
    let ptr = malloc(len, 1) >>> 0;

    const mem = getUint8ArrayMemory0();

    let offset = 0;

    for (; offset < len; offset++) {
        const code = arg.charCodeAt(offset);
        if (code > 0x7F) break;
        mem[ptr + offset] = code;
    }
    if (offset !== len) {
        if (offset !== 0) {
            arg = arg.slice(offset);
        }
        ptr = realloc(ptr, len, len = offset + arg.length * 3, 1) >>> 0;
        const view = getUint8ArrayMemory0().subarray(ptr + offset, ptr + len);
        const ret = cachedTextEncoder.encodeInto(arg, view);

        offset += ret.written;
        ptr = realloc(ptr, len, offset, 1) >>> 0;
    }

    WASM_VECTOR_LEN = offset;
    return ptr;
}

function takeFromExternrefTable0(idx) {
    const value = wasm.__wbindgen_externrefs.get(idx);
    wasm.__externref_table_dealloc(idx);
    return value;
}

let cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
cachedTextDecoder.decode();
function decodeText(ptr, len) {
    return cachedTextDecoder.decode(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}

const cachedTextEncoder = new TextEncoder();

if (!('encodeInto' in cachedTextEncoder)) {
    cachedTextEncoder.encodeInto = function (arg, view) {
        const buf = cachedTextEncoder.encode(arg);
        view.set(buf);
        return {
            read: arg.length,
            written: buf.length
        };
    }
}

let WASM_VECTOR_LEN = 0;

function wasm_bindgen_477d7a3ba2469c5b___convert__closures_____invoke___wasm_bindgen_477d7a3ba2469c5b___JsValue_____(arg0, arg1, arg2) {
    wasm.wasm_bindgen_477d7a3ba2469c5b___convert__closures_____invoke___wasm_bindgen_477d7a3ba2469c5b___JsValue_____(arg0, arg1, arg2);
}

function wasm_bindgen_477d7a3ba2469c5b___convert__closures_____invoke___wasm_bindgen_477d7a3ba2469c5b___JsValue__wasm_bindgen_477d7a3ba2469c5b___JsValue_____(arg0, arg1, arg2, arg3) {
    wasm.wasm_bindgen_477d7a3ba2469c5b___convert__closures_____invoke___wasm_bindgen_477d7a3ba2469c5b___JsValue__wasm_bindgen_477d7a3ba2469c5b___JsValue_____(arg0, arg1, arg2, arg3);
}

const ModuleInfoFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_moduleinfo_free(ptr >>> 0, 1));

/**
 * Get information about the WASM module
 */
class ModuleInfo {
    static __wrap(ptr) {
        ptr = ptr >>> 0;
        const obj = Object.create(ModuleInfo.prototype);
        obj.__wbg_ptr = ptr;
        ModuleInfoFinalization.register(obj, obj.__wbg_ptr, obj);
        return obj;
    }
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        ModuleInfoFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_moduleinfo_free(ptr, 0);
    }
    /**
     * Get the module name
     * @returns {string}
     */
    name() {
        const ret = wasm.moduleinfo_name(this.__wbg_ptr);
        var v1 = getCachedStringFromWasm0(ret[0], ret[1]);
        if (ret[0] !== 0) { wasm.__wbindgen_free(ret[0], ret[1], 1); }
        return v1;
    }
    /**
     * Get the module version
     * @returns {string}
     */
    version() {
        const ret = wasm.moduleinfo_version(this.__wbg_ptr);
        var v1 = getCachedStringFromWasm0(ret[0], ret[1]);
        if (ret[0] !== 0) { wasm.__wbindgen_free(ret[0], ret[1], 1); }
        return v1;
    }
}
if (Symbol.dispose) ModuleInfo.prototype[Symbol.dispose] = ModuleInfo.prototype.free;
exports.ModuleInfo = ModuleInfo;

/**
 * Batch extract from multiple byte arrays (asynchronous).
 *
 * Asynchronously processes multiple document byte arrays in parallel.
 * Non-blocking alternative to `batchExtractBytesSync`.
 *
 * # JavaScript Parameters
 *
 * * `dataList: Uint8Array[]` - Array of document bytes
 * * `mimeTypes: string[]` - Array of MIME types (must match dataList length)
 * * `config?: object` - Optional extraction configuration (applied to all)
 *
 * # Returns
 *
 * `Promise<object[]>` - Promise resolving to array of ExtractionResults
 *
 * # Throws
 *
 * Rejects if dataList and mimeTypes lengths don't match.
 *
 * # Example
 *
 * ```javascript
 * import { batchExtractBytes } from '@kreuzberg/wasm';
 *
 * const responses = await Promise.all([
 *   fetch('doc1.pdf'),
 *   fetch('doc2.docx')
 * ]);
 *
 * const buffers = await Promise.all(
 *   responses.map(r => r.arrayBuffer().then(b => new Uint8Array(b)))
 * );
 *
 * const results = await batchExtractBytes(
 *   buffers,
 *   ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
 *   null
 * );
 * ```
 * @param {Uint8Array[]} data_list
 * @param {string[]} mime_types
 * @param {any | null} [config]
 * @returns {Promise<any>}
 */
function batchExtractBytes(data_list, mime_types, config) {
    const ptr0 = passArrayJsValueToWasm0(data_list, wasm.__wbindgen_malloc);
    const len0 = WASM_VECTOR_LEN;
    const ptr1 = passArrayJsValueToWasm0(mime_types, wasm.__wbindgen_malloc);
    const len1 = WASM_VECTOR_LEN;
    const ret = wasm.batchExtractBytes(ptr0, len0, ptr1, len1, isLikeNone(config) ? 0 : addToExternrefTable0(config));
    return ret;
}
exports.batchExtractBytes = batchExtractBytes;

/**
 * Batch extract from multiple byte arrays (synchronous).
 *
 * Processes multiple document byte arrays in parallel. All documents use the
 * same extraction configuration.
 *
 * # JavaScript Parameters
 *
 * * `dataList: Uint8Array[]` - Array of document bytes
 * * `mimeTypes: string[]` - Array of MIME types (must match dataList length)
 * * `config?: object` - Optional extraction configuration (applied to all)
 *
 * # Returns
 *
 * `object[]` - Array of ExtractionResults in the same order as inputs
 *
 * # Throws
 *
 * Throws if dataList and mimeTypes lengths don't match.
 *
 * # Example
 *
 * ```javascript
 * import { batchExtractBytesSync } from '@kreuzberg/wasm';
 *
 * const buffers = [buffer1, buffer2, buffer3];
 * const mimeTypes = ['application/pdf', 'text/plain', 'image/png'];
 * const results = batchExtractBytesSync(buffers, mimeTypes, null);
 *
 * results.forEach((result, i) => {
 *   console.log(`Document ${i}: ${result.content.substring(0, 50)}...`);
 * });
 * ```
 * @param {Uint8Array[]} data_list
 * @param {string[]} mime_types
 * @param {any | null} [config]
 * @returns {any}
 */
function batchExtractBytesSync(data_list, mime_types, config) {
    const ptr0 = passArrayJsValueToWasm0(data_list, wasm.__wbindgen_malloc);
    const len0 = WASM_VECTOR_LEN;
    const ptr1 = passArrayJsValueToWasm0(mime_types, wasm.__wbindgen_malloc);
    const len1 = WASM_VECTOR_LEN;
    const ret = wasm.batchExtractBytesSync(ptr0, len0, ptr1, len1, isLikeNone(config) ? 0 : addToExternrefTable0(config));
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.batchExtractBytesSync = batchExtractBytesSync;

/**
 * Batch extract from multiple Files or Blobs (asynchronous).
 *
 * Processes multiple web File or Blob objects in parallel using the FileReader API.
 * Only available in browser environments.
 *
 * # JavaScript Parameters
 *
 * * `files: (File | Blob)[]` - Array of files or blobs to extract
 * * `config?: object` - Optional extraction configuration (applied to all)
 *
 * # Returns
 *
 * `Promise<object[]>` - Promise resolving to array of ExtractionResults
 *
 * # Example
 *
 * ```javascript
 * import { batchExtractFiles } from '@kreuzberg/wasm';
 *
 * // From file input with multiple files
 * const fileInput = document.getElementById('file-input');
 * const files = Array.from(fileInput.files);
 *
 * const results = await batchExtractFiles(files, null);
 * console.log(`Processed ${results.length} files`);
 * ```
 * @param {File[]} files
 * @param {any | null} [config]
 * @returns {Promise<any>}
 */
function batchExtractFiles(files, config) {
    const ptr0 = passArrayJsValueToWasm0(files, wasm.__wbindgen_malloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.batchExtractFiles(ptr0, len0, isLikeNone(config) ? 0 : addToExternrefTable0(config));
    return ret;
}
exports.batchExtractFiles = batchExtractFiles;

/**
 * Batch extract from multiple files (synchronous) - NOT AVAILABLE IN WASM.
 *
 * File system operations are not available in WebAssembly environments.
 * Use `batchExtractBytesSync` or `batchExtractBytes` instead.
 *
 * # Throws
 *
 * Always throws: "File operations are not available in WASM. Use batchExtractBytesSync or batchExtractBytes instead."
 * @returns {any}
 */
function batchExtractFilesSync() {
    const ret = wasm.batchExtractFilesSync();
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.batchExtractFilesSync = batchExtractFilesSync;

/**
 * Clear all registered OCR backends.
 *
 * # Returns
 *
 * Ok if clearing succeeds, Err if an error occurs.
 *
 * # Example
 *
 * ```javascript
 * clearOcrBackends();
 * ```
 */
function clear_ocr_backends() {
    const ret = wasm.clear_ocr_backends();
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.clear_ocr_backends = clear_ocr_backends;

/**
 * Clear all registered post-processors.
 *
 * # Returns
 *
 * Ok if clearing succeeds, Err if an error occurs.
 *
 * # Example
 *
 * ```javascript
 * clearPostProcessors();
 * ```
 */
function clear_post_processors() {
    const ret = wasm.clear_post_processors();
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.clear_post_processors = clear_post_processors;

/**
 * Clear all registered validators.
 *
 * # Returns
 *
 * Ok if clearing succeeds, Err if an error occurs.
 *
 * # Example
 *
 * ```javascript
 * clearValidators();
 * ```
 */
function clear_validators() {
    const ret = wasm.clear_validators();
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.clear_validators = clear_validators;

/**
 * Detect MIME type from raw file bytes.
 *
 * Uses magic byte signatures and content analysis to detect the MIME type of
 * a document from its binary content. Falls back to text detection if binary
 * detection fails.
 *
 * # JavaScript Parameters
 *
 * * `data: Uint8Array` - The raw file bytes
 *
 * # Returns
 *
 * `string` - The detected MIME type (e.g., "application/pdf", "image/png")
 *
 * # Throws
 *
 * Throws an error if MIME type cannot be determined from the content.
 *
 * # Example
 *
 * ```javascript
 * import { detectMimeFromBytes } from '@kreuzberg/wasm';
 * import { readFileSync } from 'fs';
 *
 * const pdfBytes = readFileSync('document.pdf');
 * const mimeType = detectMimeFromBytes(new Uint8Array(pdfBytes));
 * console.log(mimeType); // "application/pdf"
 * ```
 * @param {Uint8Array} data
 * @returns {string}
 */
function detectMimeFromBytes(data) {
    const ret = wasm.detectMimeFromBytes(data);
    if (ret[3]) {
        throw takeFromExternrefTable0(ret[2]);
    }
    var v1 = getCachedStringFromWasm0(ret[0], ret[1]);
    if (ret[0] !== 0) { wasm.__wbindgen_free(ret[0], ret[1], 1); }
    return v1;
}
exports.detectMimeFromBytes = detectMimeFromBytes;

/**
 * Discover configuration file in the project hierarchy.
 *
 * In WebAssembly environments, configuration discovery is not available because
 * there is no file system access. This function always returns an error with a
 * descriptive message directing users to use `loadConfigFromString()` instead.
 *
 * # JavaScript Parameters
 *
 * None
 *
 * # Returns
 *
 * Never returns successfully.
 *
 * # Throws
 *
 * Always throws an error with message:
 * "discoverConfig is not available in WebAssembly (no file system access). Use loadConfigFromString() instead."
 *
 * # Example
 *
 * ```javascript
 * import { discoverConfig } from '@kreuzberg/wasm';
 *
 * try {
 *   const config = discoverConfig();
 * } catch (e) {
 *   console.error(e.message);
 *   // "discoverConfig is not available in WebAssembly (no file system access).
 *   // Use loadConfigFromString() instead."
 * }
 * ```
 * @returns {any}
 */
function discoverConfig() {
    const ret = wasm.discoverConfig();
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.discoverConfig = discoverConfig;

/**
 * Extract content from a byte array (asynchronous).
 *
 * Asynchronously extracts text, tables, images, and metadata from a document.
 * Non-blocking alternative to `extractBytesSync` suitable for large documents
 * or browser environments.
 *
 * # JavaScript Parameters
 *
 * * `data: Uint8Array` - The document bytes to extract
 * * `mimeType: string` - MIME type of the data (e.g., "application/pdf")
 * * `config?: object` - Optional extraction configuration
 *
 * # Returns
 *
 * `Promise<object>` - Promise resolving to ExtractionResult
 *
 * # Throws
 *
 * Rejects if data is malformed or MIME type is unsupported.
 *
 * # Example
 *
 * ```javascript
 * import { extractBytes } from '@kreuzberg/wasm';
 *
 * // Fetch from URL
 * const response = await fetch('document.pdf');
 * const arrayBuffer = await response.arrayBuffer();
 * const data = new Uint8Array(arrayBuffer);
 *
 * const result = await extractBytes(data, 'application/pdf', null);
 * console.log(result.content.substring(0, 100));
 * ```
 * @param {Uint8Array} data
 * @param {string} mime_type
 * @param {any | null} [config]
 * @returns {Promise<any>}
 */
function extractBytes(data, mime_type, config) {
    const ptr0 = passStringToWasm0(mime_type, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.extractBytes(data, ptr0, len0, isLikeNone(config) ? 0 : addToExternrefTable0(config));
    return ret;
}
exports.extractBytes = extractBytes;

/**
 * Extract content from a byte array (synchronous).
 *
 * Extracts text, tables, images, and metadata from a document represented as bytes.
 * This is a synchronous, blocking operation suitable for smaller documents or when
 * async execution is not available.
 *
 * # JavaScript Parameters
 *
 * * `data: Uint8Array` - The document bytes to extract
 * * `mimeType: string` - MIME type of the data (e.g., "application/pdf", "image/png")
 * * `config?: object` - Optional extraction configuration
 *
 * # Returns
 *
 * `object` - ExtractionResult with extracted content and metadata
 *
 * # Throws
 *
 * Throws an error if data is malformed or MIME type is unsupported.
 *
 * # Example
 *
 * ```javascript
 * import { extractBytesSync } from '@kreuzberg/wasm';
 * import { readFileSync } from 'fs';
 *
 * const buffer = readFileSync('document.pdf');
 * const data = new Uint8Array(buffer);
 * const result = extractBytesSync(data, 'application/pdf', null);
 * console.log(result.content);
 * ```
 * @param {Uint8Array} data
 * @param {string} mime_type
 * @param {any | null} [config]
 * @returns {any}
 */
function extractBytesSync(data, mime_type, config) {
    const ptr0 = passStringToWasm0(mime_type, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.extractBytesSync(data, ptr0, len0, isLikeNone(config) ? 0 : addToExternrefTable0(config));
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.extractBytesSync = extractBytesSync;

/**
 * Extract content from a web File or Blob (asynchronous).
 *
 * Extracts content from a web File (from `<input type="file">`) or Blob object
 * using the FileReader API. Only available in browser environments.
 *
 * # JavaScript Parameters
 *
 * * `file: File | Blob` - The file or blob to extract
 * * `mimeType?: string` - Optional MIME type hint (auto-detected if omitted)
 * * `config?: object` - Optional extraction configuration
 *
 * # Returns
 *
 * `Promise<object>` - Promise resolving to ExtractionResult
 *
 * # Throws
 *
 * Rejects if file cannot be read or is malformed.
 *
 * # Example
 *
 * ```javascript
 * import { extractFile } from '@kreuzberg/wasm';
 *
 * // From file input
 * const fileInput = document.getElementById('file-input');
 * const file = fileInput.files[0];
 *
 * const result = await extractFile(file, null, null);
 * console.log(`Extracted ${result.content.length} characters`);
 * ```
 * @param {File} file
 * @param {string | null} [mime_type]
 * @param {any | null} [config]
 * @returns {Promise<any>}
 */
function extractFile(file, mime_type, config) {
    var ptr0 = isLikeNone(mime_type) ? 0 : passStringToWasm0(mime_type, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    var len0 = WASM_VECTOR_LEN;
    const ret = wasm.extractFile(file, ptr0, len0, isLikeNone(config) ? 0 : addToExternrefTable0(config));
    return ret;
}
exports.extractFile = extractFile;

/**
 * Extract content from a file (synchronous) - NOT AVAILABLE IN WASM.
 *
 * File system operations are not available in WebAssembly environments.
 * Use `extractBytesSync` or `extractBytes` instead.
 *
 * # Throws
 *
 * Always throws: "File operations are not available in WASM. Use extractBytesSync or extractBytes instead."
 * @returns {any}
 */
function extractFileSync() {
    const ret = wasm.extractFileSync();
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.extractFileSync = extractFileSync;

/**
 * Get file extensions for a given MIME type.
 *
 * Looks up all known file extensions that correspond to the specified MIME type.
 * Returns a JavaScript Array of extension strings (without leading dots).
 *
 * # JavaScript Parameters
 *
 * * `mimeType: string` - The MIME type to look up (e.g., "application/pdf")
 *
 * # Returns
 *
 * `string[]` - Array of file extensions for the MIME type
 *
 * # Throws
 *
 * Throws an error if the MIME type is not recognized.
 *
 * # Example
 *
 * ```javascript
 * import { getExtensionsForMime } from '@kreuzberg/wasm';
 *
 * const pdfExts = getExtensionsForMime('application/pdf');
 * console.log(pdfExts); // ["pdf"]
 *
 * const jpegExts = getExtensionsForMime('image/jpeg');
 * console.log(jpegExts); // ["jpg", "jpeg"]
 * ```
 * @param {string} mime_type
 * @returns {Array<any>}
 */
function getExtensionsForMime(mime_type) {
    const ptr0 = passStringToWasm0(mime_type, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.getExtensionsForMime(ptr0, len0);
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.getExtensionsForMime = getExtensionsForMime;

/**
 * Get MIME type from file extension.
 *
 * Looks up the MIME type associated with a given file extension.
 * Returns None if the extension is not recognized.
 *
 * # JavaScript Parameters
 *
 * * `extension: string` - The file extension (with or without leading dot)
 *
 * # Returns
 *
 * `string | null` - The MIME type if found, null otherwise
 *
 * # Example
 *
 * ```javascript
 * import { getMimeFromExtension } from '@kreuzberg/wasm';
 *
 * const pdfMime = getMimeFromExtension('pdf');
 * console.log(pdfMime); // "application/pdf"
 *
 * const docMime = getMimeFromExtension('docx');
 * console.log(docMime); // "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
 *
 * const unknownMime = getMimeFromExtension('unknown');
 * console.log(unknownMime); // null
 * ```
 * @param {string} extension
 * @returns {string}
 */
function getMimeFromExtension(extension) {
    const ptr0 = passStringToWasm0(extension, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.getMimeFromExtension(ptr0, len0);
    var v2 = getCachedStringFromWasm0(ret[0], ret[1]);
    if (ret[0] !== 0) { wasm.__wbindgen_free(ret[0], ret[1], 1); }
    return v2;
}
exports.getMimeFromExtension = getMimeFromExtension;

/**
 * Get module information
 * @returns {ModuleInfo}
 */
function get_module_info() {
    const ret = wasm.get_module_info();
    return ModuleInfo.__wrap(ret);
}
exports.get_module_info = get_module_info;

/**
 * Initialize the WASM module
 * This function should be called once at application startup
 */
function init() {
    wasm.init();
}
exports.init = init;

/**
 * @param {number} _num_threads
 * @returns {Promise<any>}
 */
function initThreadPool(_num_threads) {
    const ret = wasm.initThreadPool(_num_threads);
    return ret;
}
exports.initThreadPool = initThreadPool;

/**
 * Helper function to initialize the thread pool with error handling
 * Accepts the number of threads to use for the thread pool.
 * Returns true if initialization succeeded, false for graceful degradation.
 *
 * This function wraps init_thread_pool with panic handling to ensure graceful
 * degradation if thread pool initialization fails. The application will continue
 * to work in single-threaded mode if the thread pool cannot be initialized.
 * @param {number} num_threads
 * @returns {boolean}
 */
function init_thread_pool_safe(num_threads) {
    const ret = wasm.init_thread_pool_safe(num_threads);
    return ret !== 0;
}
exports.init_thread_pool_safe = init_thread_pool_safe;

/**
 * Establishes a binding between an external Pdfium WASM module and `pdfium-render`'s WASM module.
 * This function should be called from Javascript once the external Pdfium WASM module has been loaded
 * into the browser. It is essential that this function is called _before_ initializing
 * `pdfium-render` from within Rust code. For an example, see:
 * <https://github.com/ajrcarey/pdfium-render/blob/master/examples/index.html>
 * @param {any} pdfium_wasm_module
 * @param {any} local_wasm_module
 * @param {boolean} debug
 * @returns {boolean}
 */
function initialize_pdfium_render(pdfium_wasm_module, local_wasm_module, debug) {
    const ret = wasm.initialize_pdfium_render(pdfium_wasm_module, local_wasm_module, debug);
    return ret !== 0;
}
exports.initialize_pdfium_render = initialize_pdfium_render;

/**
 * List all registered OCR backend names.
 *
 * # Returns
 *
 * Array of OCR backend names, or Err if an error occurs.
 *
 * # Example
 *
 * ```javascript
 * const backends = listOcrBackends();
 * console.log(backends); // ["tesseract", "custom-ocr", ...]
 * ```
 * @returns {Array<any>}
 */
function list_ocr_backends() {
    const ret = wasm.list_ocr_backends();
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.list_ocr_backends = list_ocr_backends;

/**
 * List all registered post-processor names.
 *
 * # Returns
 *
 * Array of post-processor names, or Err if an error occurs.
 *
 * # Example
 *
 * ```javascript
 * const processors = listPostProcessors();
 * console.log(processors); // ["my-post-processor", ...]
 * ```
 * @returns {Array<any>}
 */
function list_post_processors() {
    const ret = wasm.list_post_processors();
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.list_post_processors = list_post_processors;

/**
 * List all registered validator names.
 *
 * # Returns
 *
 * Array of validator names, or Err if an error occurs.
 *
 * # Example
 *
 * ```javascript
 * const validators = listValidators();
 * console.log(validators); // ["min-content-length", ...]
 * ```
 * @returns {Array<any>}
 */
function list_validators() {
    const ret = wasm.list_validators();
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.list_validators = list_validators;

/**
 * Load configuration from a string in the specified format.
 *
 * Parses configuration content from TOML, YAML, or JSON formats and returns
 * a JavaScript object representing the ExtractionConfig. This is the primary
 * way to load configuration in WebAssembly environments since file system
 * access is not available.
 *
 * # JavaScript Parameters
 *
 * * `content: string` - The configuration content as a string
 * * `format: string` - The format of the content: "toml", "yaml", or "json"
 *
 * # Returns
 *
 * `object` - JavaScript object representing the ExtractionConfig
 *
 * # Throws
 *
 * Throws an error if:
 * - The content is invalid for the specified format
 * - The format is not one of "toml", "yaml", or "json"
 * - Required configuration fields are missing or invalid
 *
 * # Example
 *
 * ```javascript
 * import { loadConfigFromString } from '@kreuzberg/wasm';
 *
 * // Load from TOML string
 * const tomlConfig = `
 * use_cache = true
 * enable_quality_processing = true
 * `;
 * const config1 = loadConfigFromString(tomlConfig, 'toml');
 * console.log(config1.use_cache); // true
 *
 * // Load from YAML string
 * const yamlConfig = `
 * use_cache: true
 * enable_quality_processing: true
 * `;
 * const config2 = loadConfigFromString(yamlConfig, 'yaml');
 *
 * // Load from JSON string
 * const jsonConfig = `{"use_cache": true, "enable_quality_processing": true}`;
 * const config3 = loadConfigFromString(jsonConfig, 'json');
 * ```
 * @param {string} content
 * @param {string} format
 * @returns {any}
 */
function loadConfigFromString(content, format) {
    const ptr0 = passStringToWasm0(content, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ptr1 = passStringToWasm0(format, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len1 = WASM_VECTOR_LEN;
    const ret = wasm.loadConfigFromString(ptr0, len0, ptr1, len1);
    if (ret[2]) {
        throw takeFromExternrefTable0(ret[1]);
    }
    return takeFromExternrefTable0(ret[0]);
}
exports.loadConfigFromString = loadConfigFromString;

/**
 * Normalize a MIME type string.
 *
 * Normalizes a MIME type by converting to lowercase and removing parameters
 * (e.g., "application/json; charset=utf-8" becomes "application/json").
 * This is useful for consistent MIME type comparison.
 *
 * # JavaScript Parameters
 *
 * * `mimeType: string` - The MIME type string to normalize
 *
 * # Returns
 *
 * `string` - The normalized MIME type
 *
 * # Example
 *
 * ```javascript
 * import { normalizeMimeType } from '@kreuzberg/wasm';
 *
 * const normalized1 = normalizeMimeType('Application/JSON');
 * console.log(normalized1); // "application/json"
 *
 * const normalized2 = normalizeMimeType('text/html; charset=utf-8');
 * console.log(normalized2); // "text/html"
 *
 * const normalized3 = normalizeMimeType('Text/Plain; charset=ISO-8859-1');
 * console.log(normalized3); // "text/plain"
 * ```
 * @param {string} mime_type
 * @returns {string}
 */
function normalizeMimeType(mime_type) {
    const ptr0 = passStringToWasm0(mime_type, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.normalizeMimeType(ptr0, len0);
    var v2 = getCachedStringFromWasm0(ret[0], ret[1]);
    if (ret[0] !== 0) { wasm.__wbindgen_free(ret[0], ret[1], 1); }
    return v2;
}
exports.normalizeMimeType = normalizeMimeType;

/**
 * A callback function that can be invoked by Pdfium's `FPDF_LoadCustomDocument()` function,
 * wrapping around `crate::utils::files::read_block_from_callback()` to shuffle data buffers
 * from our WASM memory heap to Pdfium's WASM memory heap as they are loaded.
 * @param {number} param
 * @param {number} position
 * @param {number} pBuf
 * @param {number} size
 * @returns {number}
 */
function read_block_from_callback_wasm(param, position, pBuf, size) {
    const ret = wasm.read_block_from_callback_wasm(param, position, pBuf, size);
    return ret;
}
exports.read_block_from_callback_wasm = read_block_from_callback_wasm;

/**
 * Register a custom OCR backend.
 *
 * # Arguments
 *
 * * `backend` - JavaScript object implementing the OcrBackendProtocol interface:
 *   - `name(): string` - Unique backend name
 *   - `supportedLanguages(): string[]` - Array of language codes the backend supports
 *   - `processImage(imageBase64: string, language: string): Promise<string>` - Process image and return JSON result
 *
 * # Returns
 *
 * Ok if registration succeeds, Err with description if it fails.
 *
 * # Example
 *
 * ```javascript
 * registerOcrBackend({
 *   name: () => "custom-ocr",
 *   supportedLanguages: () => ["en", "es", "fr"],
 *   processImage: async (imageBase64, language) => {
 *     const buffer = Buffer.from(imageBase64, "base64");
 *     // Process image with custom OCR engine
 *     const text = await customOcrEngine.recognize(buffer, language);
 *     return JSON.stringify({
 *       content: text,
 *       mime_type: "text/plain",
 *       metadata: {}
 *     });
 *   }
 * });
 * ```
 * @param {any} backend
 */
function register_ocr_backend(backend) {
    const ret = wasm.register_ocr_backend(backend);
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.register_ocr_backend = register_ocr_backend;

/**
 * Register a custom post-processor.
 *
 * # Arguments
 *
 * * `processor` - JavaScript object implementing the PostProcessorProtocol interface:
 *   - `name(): string` - Unique processor name
 *   - `process(jsonString: string): Promise<string>` - Process function that takes JSON input
 *   - `processingStage(): "early" | "middle" | "late"` - Optional processing stage (defaults to "middle")
 *
 * # Returns
 *
 * Ok if registration succeeds, Err with description if it fails.
 *
 * # Example
 *
 * ```javascript
 * registerPostProcessor({
 *   name: () => "my-post-processor",
 *   processingStage: () => "middle",
 *   process: async (jsonString) => {
 *     const result = JSON.parse(jsonString);
 *     // Process the extraction result
 *     result.metadata.processed_by = "my-post-processor";
 *     return JSON.stringify(result);
 *   }
 * });
 * ```
 * @param {any} processor
 */
function register_post_processor(processor) {
    const ret = wasm.register_post_processor(processor);
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.register_post_processor = register_post_processor;

/**
 * Register a custom validator.
 *
 * # Arguments
 *
 * * `validator` - JavaScript object implementing the ValidatorProtocol interface:
 *   - `name(): string` - Unique validator name
 *   - `validate(jsonString: string): Promise<string>` - Validation function returning empty string on success, error message on failure
 *   - `priority(): number` - Optional priority (defaults to 50, higher runs first)
 *
 * # Returns
 *
 * Ok if registration succeeds, Err with description if it fails.
 *
 * # Example
 *
 * ```javascript
 * registerValidator({
 *   name: () => "min-content-length",
 *   priority: () => 100,
 *   validate: async (jsonString) => {
 *     const result = JSON.parse(jsonString);
 *     if (result.content.length < 100) {
 *       return "Content too short"; // Validation failure
 *     }
 *     return ""; // Success
 *   }
 * });
 * ```
 * @param {any} validator
 */
function register_validator(validator) {
    const ret = wasm.register_validator(validator);
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.register_validator = register_validator;

/**
 * Unregister an OCR backend by name.
 *
 * # Arguments
 *
 * * `name` - Name of the OCR backend to unregister
 *
 * # Returns
 *
 * Ok if unregistration succeeds, Err if the backend is not found or other error occurs.
 *
 * # Example
 *
 * ```javascript
 * unregisterOcrBackend("custom-ocr");
 * ```
 * @param {string} name
 */
function unregister_ocr_backend(name) {
    const ptr0 = passStringToWasm0(name, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.unregister_ocr_backend(ptr0, len0);
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.unregister_ocr_backend = unregister_ocr_backend;

/**
 * Unregister a post-processor by name.
 *
 * # Arguments
 *
 * * `name` - Name of the post-processor to unregister
 *
 * # Returns
 *
 * Ok if unregistration succeeds, Err if the processor is not found or other error occurs.
 *
 * # Example
 *
 * ```javascript
 * unregisterPostProcessor("my-post-processor");
 * ```
 * @param {string} name
 */
function unregister_post_processor(name) {
    const ptr0 = passStringToWasm0(name, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.unregister_post_processor(ptr0, len0);
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.unregister_post_processor = unregister_post_processor;

/**
 * Unregister a validator by name.
 *
 * # Arguments
 *
 * * `name` - Name of the validator to unregister
 *
 * # Returns
 *
 * Ok if unregistration succeeds, Err if the validator is not found or other error occurs.
 *
 * # Example
 *
 * ```javascript
 * unregisterValidator("min-content-length");
 * ```
 * @param {string} name
 */
function unregister_validator(name) {
    const ptr0 = passStringToWasm0(name, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.unregister_validator(ptr0, len0);
    if (ret[1]) {
        throw takeFromExternrefTable0(ret[0]);
    }
}
exports.unregister_validator = unregister_validator;

/**
 * Version of the kreuzberg-wasm binding
 * @returns {string}
 */
function version() {
    const ret = wasm.version();
    var v1 = getCachedStringFromWasm0(ret[0], ret[1]);
    if (ret[0] !== 0) { wasm.__wbindgen_free(ret[0], ret[1], 1); }
    return v1;
}
exports.version = version;

/**
 * A callback function that can be invoked by Pdfium's `FPDF_SaveAsCopy()` and `FPDF_SaveWithVersion()`
 * functions, wrapping around `crate::utils::files::write_block_from_callback()` to shuffle data buffers
 * from Pdfium's WASM memory heap to our WASM memory heap as they are written.
 * @param {number} param
 * @param {number} buf
 * @param {number} size
 * @returns {number}
 */
function write_block_from_callback_wasm(param, buf, size) {
    const ret = wasm.write_block_from_callback_wasm(param, buf, size);
    return ret;
}
exports.write_block_from_callback_wasm = write_block_from_callback_wasm;

exports.__wbg_Error_52673b7de5a0ca89 = function(arg0, arg1) {
    var v0 = getCachedStringFromWasm0(arg0, arg1);
    const ret = Error(v0);
    return ret;
};

exports.__wbg_Number_2d1dcfcf4ec51736 = function(arg0) {
    const ret = Number(arg0);
    return ret;
};

exports.__wbg_String_8f0eb39a4a4c2f66 = function(arg0, arg1) {
    const ret = String(arg1);
    const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len1 = WASM_VECTOR_LEN;
    getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
};

exports.__wbg___wbindgen_bigint_get_as_i64_6e32f5e6aff02e1d = function(arg0, arg1) {
    const v = arg1;
    const ret = typeof(v) === 'bigint' ? v : undefined;
    getDataViewMemory0().setBigInt64(arg0 + 8 * 1, isLikeNone(ret) ? BigInt(0) : ret, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, !isLikeNone(ret), true);
};

exports.__wbg___wbindgen_boolean_get_dea25b33882b895b = function(arg0) {
    const v = arg0;
    const ret = typeof(v) === 'boolean' ? v : undefined;
    return isLikeNone(ret) ? 0xFFFFFF : ret ? 1 : 0;
};

exports.__wbg___wbindgen_debug_string_adfb662ae34724b6 = function(arg0, arg1) {
    const ret = debugString(arg1);
    const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len1 = WASM_VECTOR_LEN;
    getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
};

exports.__wbg___wbindgen_in_0d3e1e8f0c669317 = function(arg0, arg1) {
    const ret = arg0 in arg1;
    return ret;
};

exports.__wbg___wbindgen_is_bigint_0e1a2e3f55cfae27 = function(arg0) {
    const ret = typeof(arg0) === 'bigint';
    return ret;
};

exports.__wbg___wbindgen_is_function_8d400b8b1af978cd = function(arg0) {
    const ret = typeof(arg0) === 'function';
    return ret;
};

exports.__wbg___wbindgen_is_object_ce774f3490692386 = function(arg0) {
    const val = arg0;
    const ret = typeof(val) === 'object' && val !== null;
    return ret;
};

exports.__wbg___wbindgen_is_string_704ef9c8fc131030 = function(arg0) {
    const ret = typeof(arg0) === 'string';
    return ret;
};

exports.__wbg___wbindgen_is_undefined_f6b95eab589e0269 = function(arg0) {
    const ret = arg0 === undefined;
    return ret;
};

exports.__wbg___wbindgen_jsval_eq_b6101cc9cef1fe36 = function(arg0, arg1) {
    const ret = arg0 === arg1;
    return ret;
};

exports.__wbg___wbindgen_jsval_loose_eq_766057600fdd1b0d = function(arg0, arg1) {
    const ret = arg0 == arg1;
    return ret;
};

exports.__wbg___wbindgen_number_get_9619185a74197f95 = function(arg0, arg1) {
    const obj = arg1;
    const ret = typeof(obj) === 'number' ? obj : undefined;
    getDataViewMemory0().setFloat64(arg0 + 8 * 1, isLikeNone(ret) ? 0 : ret, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, !isLikeNone(ret), true);
};

exports.__wbg___wbindgen_string_get_a2a31e16edf96e42 = function(arg0, arg1) {
    const obj = arg1;
    const ret = typeof(obj) === 'string' ? obj : undefined;
    var ptr1 = isLikeNone(ret) ? 0 : passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    var len1 = WASM_VECTOR_LEN;
    getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
};

exports.__wbg___wbindgen_throw_dd24417ed36fc46e = function(arg0, arg1) {
    var v0 = getCachedStringFromWasm0(arg0, arg1);
    throw new Error(v0);
};

exports.__wbg__wbg_cb_unref_87dfb5aaa0cbcea7 = function(arg0) {
    arg0._wbg_cb_unref();
};

exports.__wbg_addEventListener_6a82629b3d430a48 = function() { return handleError(function (arg0, arg1, arg2, arg3) {
    var v0 = getCachedStringFromWasm0(arg1, arg2);
    arg0.addEventListener(v0, arg3);
}, arguments) };

exports.__wbg_apply_52e9ae668d017009 = function() { return handleError(function (arg0, arg1, arg2) {
    const ret = arg0.apply(arg1, arg2);
    return ret;
}, arguments) };

exports.__wbg_call_3020136f7a2d6e44 = function() { return handleError(function (arg0, arg1, arg2) {
    const ret = arg0.call(arg1, arg2);
    return ret;
}, arguments) };

exports.__wbg_call_abb4ff46ce38be40 = function() { return handleError(function (arg0, arg1) {
    const ret = arg0.call(arg1);
    return ret;
}, arguments) };

exports.__wbg_call_c8baa5c5e72d274e = function() { return handleError(function (arg0, arg1, arg2, arg3) {
    const ret = arg0.call(arg1, arg2, arg3);
    return ret;
}, arguments) };

exports.__wbg_construct_8d61a09a064d7a0e = function() { return handleError(function (arg0, arg1) {
    const ret = Reflect.construct(arg0, arg1);
    return ret;
}, arguments) };

exports.__wbg_debug_9d0c87ddda3dc485 = function(arg0) {
    console.debug(arg0);
};

exports.__wbg_decode_47d91d32f8c229af = function() { return handleError(function (arg0, arg1, arg2, arg3) {
    const ret = arg1.decode(getArrayU8FromWasm0(arg2, arg3));
    const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len1 = WASM_VECTOR_LEN;
    getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
}, arguments) };

exports.__wbg_done_62ea16af4ce34b24 = function(arg0) {
    const ret = arg0.done;
    return ret;
};

exports.__wbg_entries_83c79938054e065f = function(arg0) {
    const ret = Object.entries(arg0);
    return ret;
};

exports.__wbg_error_7534b8e9a36f1ab4 = function(arg0, arg1) {
    var v0 = getCachedStringFromWasm0(arg0, arg1);
    if (arg0 !== 0) { wasm.__wbindgen_free(arg0, arg1, 1); }
    console.error(v0);
};

exports.__wbg_error_7bc7d576a6aaf855 = function(arg0) {
    console.error(arg0);
};

exports.__wbg_from_29a8414a7a7cd19d = function(arg0) {
    const ret = Array.from(arg0);
    return ret;
};

exports.__wbg_getRandomValues_1c61fac11405ffdc = function() { return handleError(function (arg0, arg1) {
    globalThis.crypto.getRandomValues(getArrayU8FromWasm0(arg0, arg1));
}, arguments) };

exports.__wbg_getTime_ad1e9878a735af08 = function(arg0) {
    const ret = arg0.getTime();
    return ret;
};

exports.__wbg_get_16458e8ef25ea5fa = function() { return handleError(function (arg0, arg1) {
    const ret = arg0.get(arg1 >>> 0);
    return ret;
}, arguments) };

exports.__wbg_get_6b7bd52aca3f9671 = function(arg0, arg1) {
    const ret = arg0[arg1 >>> 0];
    return ret;
};

exports.__wbg_get_af9dab7e9603ea93 = function() { return handleError(function (arg0, arg1) {
    const ret = Reflect.get(arg0, arg1);
    return ret;
}, arguments) };

exports.__wbg_get_index_4e7b3f629a0ab9cd = function(arg0, arg1) {
    const ret = arg0[arg1 >>> 0];
    return ret;
};

exports.__wbg_get_with_ref_key_1dc361bd10053bfe = function(arg0, arg1) {
    const ret = arg0[arg1];
    return ret;
};

exports.__wbg_info_ce6bcc489c22f6f0 = function(arg0) {
    console.info(arg0);
};

exports.__wbg_instanceof_ArrayBuffer_f3320d2419cd0355 = function(arg0) {
    let result;
    try {
        result = arg0 instanceof ArrayBuffer;
    } catch (_) {
        result = false;
    }
    const ret = result;
    return ret;
};

exports.__wbg_instanceof_Map_084be8da74364158 = function(arg0) {
    let result;
    try {
        result = arg0 instanceof Map;
    } catch (_) {
        result = false;
    }
    const ret = result;
    return ret;
};

exports.__wbg_instanceof_Uint8Array_da54ccc9d3e09434 = function(arg0) {
    let result;
    try {
        result = arg0 instanceof Uint8Array;
    } catch (_) {
        result = false;
    }
    const ret = result;
    return ret;
};

exports.__wbg_isArray_51fd9e6422c0a395 = function(arg0) {
    const ret = Array.isArray(arg0);
    return ret;
};

exports.__wbg_isSafeInteger_ae7d3f054d55fa16 = function(arg0) {
    const ret = Number.isSafeInteger(arg0);
    return ret;
};

exports.__wbg_iterator_27b7c8b35ab3e86b = function() {
    const ret = Symbol.iterator;
    return ret;
};

exports.__wbg_length_22ac23eaec9d8053 = function(arg0) {
    const ret = arg0.length;
    return ret;
};

exports.__wbg_length_3a9ca660d3d3391b = function(arg0) {
    const ret = arg0.length;
    return ret;
};

exports.__wbg_length_bd124cfd1a9444fe = function(arg0) {
    const ret = arg0.length;
    return ret;
};

exports.__wbg_length_d45040a40c570362 = function(arg0) {
    const ret = arg0.length;
    return ret;
};

exports.__wbg_log_1d990106d99dacb7 = function(arg0) {
    console.log(arg0);
};

exports.__wbg_new_0_23cedd11d9b40c9d = function() {
    const ret = new Date();
    return ret;
};

exports.__wbg_new_111dde64cffa8ba1 = function() { return handleError(function () {
    const ret = new FileReader();
    return ret;
}, arguments) };

exports.__wbg_new_1ba21ce319a06297 = function() {
    const ret = new Object();
    return ret;
};

exports.__wbg_new_25f239778d6112b9 = function() {
    const ret = new Array();
    return ret;
};

exports.__wbg_new_6421f6084cc5bc5a = function(arg0) {
    const ret = new Uint8Array(arg0);
    return ret;
};

exports.__wbg_new_8a6f238a6ece86ea = function() {
    const ret = new Error();
    return ret;
};

exports.__wbg_new_b546ae120718850e = function() {
    const ret = new Map();
    return ret;
};

exports.__wbg_new_ff12d2b041fb48f1 = function(arg0, arg1) {
    try {
        var state0 = {a: arg0, b: arg1};
        var cb0 = (arg0, arg1) => {
            const a = state0.a;
            state0.a = 0;
            try {
                return wasm_bindgen_477d7a3ba2469c5b___convert__closures_____invoke___wasm_bindgen_477d7a3ba2469c5b___JsValue__wasm_bindgen_477d7a3ba2469c5b___JsValue_____(a, state0.b, arg0, arg1);
            } finally {
                state0.a = a;
            }
        };
        const ret = new Promise(cb0);
        return ret;
    } finally {
        state0.a = state0.b = 0;
    }
};

exports.__wbg_new_no_args_cb138f77cf6151ee = function(arg0, arg1) {
    var v0 = getCachedStringFromWasm0(arg0, arg1);
    const ret = new Function(v0);
    return ret;
};

exports.__wbg_new_with_label_a21974f868c72f0c = function() { return handleError(function (arg0, arg1) {
    var v0 = getCachedStringFromWasm0(arg0, arg1);
    const ret = new TextDecoder(v0);
    return ret;
}, arguments) };

exports.__wbg_new_with_length_12c6de4fac33117a = function(arg0) {
    const ret = new Array(arg0 >>> 0);
    return ret;
};

exports.__wbg_next_138a17bbf04e926c = function(arg0) {
    const ret = arg0.next;
    return ret;
};

exports.__wbg_next_3cfe5c0fe2a4cc53 = function() { return handleError(function (arg0) {
    const ret = arg0.next();
    return ret;
}, arguments) };

exports.__wbg_of_122077a9318f8376 = function(arg0, arg1, arg2, arg3, arg4) {
    const ret = Array.of(arg0, arg1, arg2, arg3, arg4);
    return ret;
};

exports.__wbg_of_6505a0eb509da02e = function(arg0) {
    const ret = Array.of(arg0);
    return ret;
};

exports.__wbg_of_7779827fa663eec8 = function(arg0, arg1, arg2) {
    const ret = Array.of(arg0, arg1, arg2);
    return ret;
};

exports.__wbg_of_b8cd42ebb79fb759 = function(arg0, arg1) {
    const ret = Array.of(arg0, arg1);
    return ret;
};

exports.__wbg_of_fdf875aa87d9498c = function(arg0, arg1, arg2, arg3) {
    const ret = Array.of(arg0, arg1, arg2, arg3);
    return ret;
};

exports.__wbg_prototypesetcall_dfe9b766cdc1f1fd = function(arg0, arg1, arg2) {
    Uint8Array.prototype.set.call(getArrayU8FromWasm0(arg0, arg1), arg2);
};

exports.__wbg_push_7d9be8f38fc13975 = function(arg0, arg1) {
    const ret = arg0.push(arg1);
    return ret;
};

exports.__wbg_queueMicrotask_9b549dfce8865860 = function(arg0) {
    const ret = arg0.queueMicrotask;
    return ret;
};

exports.__wbg_queueMicrotask_fca69f5bfad613a5 = function(arg0) {
    queueMicrotask(arg0);
};

exports.__wbg_readAsArrayBuffer_0aca937439be3197 = function() { return handleError(function (arg0, arg1) {
    arg0.readAsArrayBuffer(arg1);
}, arguments) };

exports.__wbg_reject_e9f21cdd3c968ce3 = function(arg0) {
    const ret = Promise.reject(arg0);
    return ret;
};

exports.__wbg_resolve_fd5bfbaa4ce36e1e = function(arg0) {
    const ret = Promise.resolve(arg0);
    return ret;
};

exports.__wbg_result_893437a1eaacc4df = function() { return handleError(function (arg0) {
    const ret = arg0.result;
    return ret;
}, arguments) };

exports.__wbg_set_3f1d0b984ed272ed = function(arg0, arg1, arg2) {
    arg0[arg1] = arg2;
};

exports.__wbg_set_7df433eea03a5c14 = function(arg0, arg1, arg2) {
    arg0[arg1 >>> 0] = arg2;
};

exports.__wbg_set_bc3a432bdcd60886 = function(arg0, arg1, arg2) {
    arg0.set(arg1, arg2 >>> 0);
};

exports.__wbg_set_c50d03a32da17043 = function() { return handleError(function (arg0, arg1, arg2) {
    arg0.set(arg1 >>> 0, arg2);
}, arguments) };

exports.__wbg_set_efaaf145b9377369 = function(arg0, arg1, arg2) {
    const ret = arg0.set(arg1, arg2);
    return ret;
};

exports.__wbg_slice_27b3dfe21d8ce752 = function(arg0, arg1, arg2) {
    const ret = arg0.slice(arg1 >>> 0, arg2 >>> 0);
    return ret;
};

exports.__wbg_stack_0ed75d68575b0f3c = function(arg0, arg1) {
    const ret = arg1.stack;
    const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len1 = WASM_VECTOR_LEN;
    getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
};

exports.__wbg_static_accessor_GLOBAL_769e6b65d6557335 = function() {
    const ret = typeof global === 'undefined' ? null : global;
    return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
};

exports.__wbg_static_accessor_GLOBAL_THIS_60cf02db4de8e1c1 = function() {
    const ret = typeof globalThis === 'undefined' ? null : globalThis;
    return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
};

exports.__wbg_static_accessor_SELF_08f5a74c69739274 = function() {
    const ret = typeof self === 'undefined' ? null : self;
    return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
};

exports.__wbg_static_accessor_WINDOW_a8924b26aa92d024 = function() {
    const ret = typeof window === 'undefined' ? null : window;
    return isLikeNone(ret) ? 0 : addToExternrefTable0(ret);
};

exports.__wbg_subarray_845f2f5bce7d061a = function(arg0, arg1, arg2) {
    const ret = arg0.subarray(arg1 >>> 0, arg2 >>> 0);
    return ret;
};

exports.__wbg_then_429f7caf1026411d = function(arg0, arg1, arg2) {
    const ret = arg0.then(arg1, arg2);
    return ret;
};

exports.__wbg_then_4f95312d68691235 = function(arg0, arg1) {
    const ret = arg0.then(arg1);
    return ret;
};

exports.__wbg_type_cb833fc71b5282fb = function(arg0, arg1) {
    const ret = arg1.type;
    const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    const len1 = WASM_VECTOR_LEN;
    getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
};

exports.__wbg_value_57b7b035e117f7ee = function(arg0) {
    const ret = arg0.value;
    return ret;
};

exports.__wbg_warn_6e567d0d926ff881 = function(arg0) {
    console.warn(arg0);
};

exports.__wbindgen_cast_4625c577ab2ec9ee = function(arg0) {
    // Cast intrinsic for `U64 -> Externref`.
    const ret = BigInt.asUintN(64, arg0);
    return ret;
};

exports.__wbindgen_cast_61cf0712ca58066e = function(arg0, arg1) {
    // Cast intrinsic for `Closure(Closure { dtor_idx: 1962, function: Function { arguments: [Externref], shim_idx: 1963, ret: Unit, inner_ret: Some(Unit) }, mutable: true }) -> Externref`.
    const ret = makeMutClosure(arg0, arg1, wasm.wasm_bindgen_477d7a3ba2469c5b___closure__destroy___dyn_core_f96ffdd67f65b3d8___ops__function__FnMut__wasm_bindgen_477d7a3ba2469c5b___JsValue____Output_______, wasm_bindgen_477d7a3ba2469c5b___convert__closures_____invoke___wasm_bindgen_477d7a3ba2469c5b___JsValue_____);
    return ret;
};

exports.__wbindgen_cast_7e9c58eeb11b0a6f = function(arg0, arg1) {
    var v0 = getCachedStringFromWasm0(arg0, arg1);
    // Cast intrinsic for `Ref(CachedString) -> Externref`.
    const ret = v0;
    return ret;
};

exports.__wbindgen_cast_9ae0607507abb057 = function(arg0) {
    // Cast intrinsic for `I64 -> Externref`.
    const ret = arg0;
    return ret;
};

exports.__wbindgen_cast_cb9088102bce6b30 = function(arg0, arg1) {
    // Cast intrinsic for `Ref(Slice(U8)) -> NamedExternref("Uint8Array")`.
    const ret = getArrayU8FromWasm0(arg0, arg1);
    return ret;
};

exports.__wbindgen_cast_d6cd19b81560fd6e = function(arg0) {
    // Cast intrinsic for `F64 -> Externref`.
    const ret = arg0;
    return ret;
};

exports.__wbindgen_init_externref_table = function() {
    const table = wasm.__wbindgen_externrefs;
    const offset = table.grow(4);
    table.set(0, undefined);
    table.set(offset + 0, undefined);
    table.set(offset + 1, null);
    table.set(offset + 2, true);
    table.set(offset + 3, false);
};

exports.__wbindgen_object_is_undefined = function(arg0) {
    const ret = arg0 === undefined;
    return ret;
};

const wasmPath = `${__dirname}/kreuzberg_wasm_bg.wasm`;
const wasmBytes = require('fs').readFileSync(wasmPath);
const wasmModule = new WebAssembly.Module(wasmBytes);
const wasm = exports.__wasm = new WebAssembly.Instance(wasmModule, imports).exports;

wasm.__wbindgen_start();
