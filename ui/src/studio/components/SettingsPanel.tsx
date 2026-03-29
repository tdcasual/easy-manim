/**
 * SettingsPanel - 参数控制面板
 * Kawaii 二次元风格
 */
import { useRef } from "react";
import { useI18n } from "../../app/locale";
import { EmojiIcon } from "../../components";
import { useDialogA11y } from "../../components/useDialogA11y";
import styles from "../styles/SettingsPanel.module.css";

export interface GenerationParams {
  resolution: "480p" | "720p" | "1080p";
  duration: "5s" | "10s" | "15s";
  style: "natural" | "vivid" | "anime" | "cinematic";
  quality: "standard" | "high" | "ultra";
}

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  params: GenerationParams;
  onParamsChange: (params: GenerationParams) => void;
}

const resolutionOptions = [
  { value: "480p" as const, label: "480p", width: 854, height: 480, emoji: "📱" },
  { value: "720p" as const, label: "720p HD", width: 1280, height: 720, emoji: "💻" },
  { value: "1080p" as const, label: "1080p FHD", width: 1920, height: 1080, emoji: "🖥️" },
];

const durationOptions = [
  {
    value: "5s" as const,
    labelKey: "studio.settings.duration.5s.label",
    descriptionKey: "studio.settings.duration.5s.description",
    emoji: "⚡",
  },
  {
    value: "10s" as const,
    labelKey: "studio.settings.duration.10s.label",
    descriptionKey: "studio.settings.duration.10s.description",
    emoji: "🎬",
  },
  {
    value: "15s" as const,
    labelKey: "studio.settings.duration.15s.label",
    descriptionKey: "studio.settings.duration.15s.description",
    emoji: "🎭",
  },
];

const styleOptions = [
  { value: "natural" as const, labelKey: "studio.settings.style.natural", color: "#81C784", emoji: "🌿" },
  { value: "vivid" as const, labelKey: "studio.settings.style.vivid", color: "#FF8A65", emoji: "🌈" },
  { value: "anime" as const, labelKey: "studio.settings.style.anime", color: "#7986CB", emoji: "🎨" },
  {
    value: "cinematic" as const,
    labelKey: "studio.settings.style.cinematic",
    color: "#4DD0E1",
    emoji: "🎬",
  },
];

const qualityOptions = [
  {
    value: "standard" as const,
    labelKey: "studio.settings.quality.standard",
    descriptionKey: "studio.settings.quality.standard.description",
    emoji: "🚀",
  },
  {
    value: "high" as const,
    labelKey: "studio.settings.quality.high",
    descriptionKey: "studio.settings.quality.high.description",
    emoji: "✨",
  },
  {
    value: "ultra" as const,
    labelKey: "studio.settings.quality.ultra",
    descriptionKey: "studio.settings.quality.ultra.description",
    emoji: "💎",
  },
];

export function SettingsPanel({ isOpen, onClose, params, onParamsChange }: SettingsPanelProps) {
  const { t } = useI18n();
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useDialogA11y({
    isOpen,
    onClose,
    dialogRef: panelRef,
    initialFocusRef: closeButtonRef,
  });

  if (!isOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div className={styles.overlay} onClick={onClose} aria-hidden="true" />

      {/* 面板 */}
      <div
        ref={panelRef}
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-label={t("studio.settings.dialog")}
      >
        {/* 头部 */}
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <EmojiIcon emoji="⚙️" color="mint" size="sm" />
            <h2>{t("studio.settings.title")}</h2>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label={t("studio.settings.close")}
            className={styles.closeButton}
          >
            <EmojiIcon emoji="✖️" color="white" size="xs" />
          </button>
        </div>

        {/* 内容 */}
        <div className={styles.content}>
          {/* 分辨率 */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <EmojiIcon emoji="🖥️" color="sky" size="xs" />
              <h3>{t("studio.settings.resolution")}</h3>
            </div>
            <div className={styles.optionsGrid3}>
              {resolutionOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => onParamsChange({ ...params, resolution: opt.value })}
                  className={
                    params.resolution === opt.value
                      ? styles.optionButtonActive
                      : styles.optionButton
                  }
                >
                  <div
                    className={
                      params.resolution === opt.value
                        ? styles.optionLabelActive
                        : styles.optionLabel
                    }
                  >
                    {opt.emoji} {opt.label}
                  </div>
                  <div className={styles.optionDescription}>
                    {opt.width}×{opt.height}
                  </div>
                </button>
              ))}
            </div>
          </section>

          {/* 时长 */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <EmojiIcon emoji="⏱️" color="peach" size="xs" />
              <h3>{t("studio.settings.duration")}</h3>
            </div>
            <div className={styles.optionsGrid3}>
              {durationOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => onParamsChange({ ...params, duration: opt.value })}
                  className={
                    params.duration === opt.value ? styles.optionButtonActive : styles.optionButton
                  }
                >
                  <div
                    className={
                      params.duration === opt.value ? styles.optionLabelActive : styles.optionLabel
                    }
                  >
                    {opt.emoji} {t(opt.labelKey)}
                  </div>
                  <div className={styles.optionDescription}>{t(opt.descriptionKey)}</div>
                </button>
              ))}
            </div>
          </section>

          {/* 风格 */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <EmojiIcon emoji="🎨" color="pink" size="xs" />
              <h3>{t("studio.settings.style")}</h3>
            </div>
            <div className={styles.optionsGrid4}>
              {styleOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => onParamsChange({ ...params, style: opt.value })}
                  className={styles.styleButton}
                  style={{
                    borderColor: params.style === opt.value ? opt.color : undefined,
                    background: params.style === opt.value ? `${opt.color}20` : undefined,
                  }}
                >
                  <span className={styles.styleEmoji}>{opt.emoji}</span>
                  <div
                    className={
                      params.style === opt.value ? styles.styleLabelActive : styles.styleLabel
                    }
                    style={{
                      color: params.style === opt.value ? opt.color : undefined,
                    }}
                  >
                    {t(opt.labelKey)}
                  </div>
                </button>
              ))}
            </div>
          </section>

          {/* 质量 */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <EmojiIcon emoji="💎" color="lavender" size="xs" />
              <h3>{t("studio.settings.quality")}</h3>
            </div>
            <div className={styles.optionsVertical}>
              {qualityOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => onParamsChange({ ...params, quality: opt.value })}
                  className={
                    params.quality === opt.value ? styles.qualityButtonActive : styles.qualityButton
                  }
                >
                  <div className={styles.qualityInfo}>
                    <div
                      className={
                        params.quality === opt.value
                          ? styles.qualityLabelActive
                          : styles.qualityLabel
                      }
                    >
                      {opt.emoji} {t(opt.labelKey)}
                    </div>
                    <div className={styles.qualityDescription}>{t(opt.descriptionKey)}</div>
                  </div>
                  {params.quality === opt.value && (
                    <div className={styles.checkIndicator}>
                      <EmojiIcon emoji="✓" color="mint" size="xs" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
