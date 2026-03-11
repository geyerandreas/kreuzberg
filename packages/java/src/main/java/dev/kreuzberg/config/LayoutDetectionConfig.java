package dev.kreuzberg.config;

import java.util.HashMap;
import java.util.Map;

/**
 * Layout detection configuration for document layout analysis.
 *
 * @since 4.4.0
 */
public final class LayoutDetectionConfig {
	private final String preset;
	private final Double confidenceThreshold;
	private final Boolean applyHeuristics;

	private LayoutDetectionConfig(Builder builder) {
		this.preset = builder.preset;
		this.confidenceThreshold = builder.confidenceThreshold;
		this.applyHeuristics = builder.applyHeuristics;
	}

	public static Builder builder() {
		return new Builder();
	}

	public String getPreset() {
		return preset;
	}

	public Double getConfidenceThreshold() {
		return confidenceThreshold;
	}

	public Boolean getApplyHeuristics() {
		return applyHeuristics;
	}

	public Map<String, Object> toMap() {
		Map<String, Object> map = new HashMap<>();
		if (preset != null) {
			map.put("preset", preset);
		}
		if (confidenceThreshold != null) {
			map.put("confidence_threshold", confidenceThreshold);
		}
		if (applyHeuristics != null) {
			map.put("apply_heuristics", applyHeuristics);
		}
		return map;
	}

	public static final class Builder {
		private String preset = "fast";
		private Double confidenceThreshold;
		private Boolean applyHeuristics = true;

		private Builder() {
		}

		public Builder preset(String preset) {
			this.preset = preset;
			return this;
		}

		public Builder confidenceThreshold(Double confidenceThreshold) {
			this.confidenceThreshold = confidenceThreshold;
			return this;
		}

		public Builder applyHeuristics(Boolean applyHeuristics) {
			this.applyHeuristics = applyHeuristics;
			return this;
		}

		public LayoutDetectionConfig build() {
			return new LayoutDetectionConfig(this);
		}
	}

	static LayoutDetectionConfig fromMap(Map<String, Object> map) {
		if (map == null) {
			return null;
		}
		Builder builder = builder();
		if (map.get("preset") instanceof String) {
			builder.preset((String) map.get("preset"));
		}
		Object confidenceThresholdValue = map.get("confidence_threshold");
		if (confidenceThresholdValue instanceof Number) {
			builder.confidenceThreshold(((Number) confidenceThresholdValue).doubleValue());
		}
		Object applyHeuristicsValue = map.get("apply_heuristics");
		if (applyHeuristicsValue instanceof Boolean) {
			builder.applyHeuristics((Boolean) applyHeuristicsValue);
		}
		return builder.build();
	}
}
