/**
 * SettingsPanel - 参数控制面板
 * Kawaii 二次元风格
 */
import { useRef, useEffect } from "react";
import { EmojiIcon } from "../../components";
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
  { value: "5s" as const, label: "5 秒", description: "快速预览", emoji: "⚡" },
  { value: "10s" as const, label: "10 秒", description: "标准长度", emoji: "🎬" },
  { value: "15s" as const, label: "15 秒", description: "详细展示", emoji: "🎭" },
];

const styleOptions = [
  { value: "natural" as const, label: "自然", color: "#81C784", emoji: "🌿" },
  { value: "vivid" as const, label: "鲜艳", color: "#FF8A65", emoji: "🌈" },
  { value: "anime" as const, label: "动漫", color: "#7986CB", emoji: "🎨" },
  { value: "cinematic" as const, label: "电影", color: "#4DD0E1", emoji: "🎬" },
];

const qualityOptions = [
  { value: "standard" as const, label: "标准", description: "生成快，省积分", emoji: "🚀" },
  { value: "high" as const, label: "高清", description: "平衡速度质量", emoji: "✨" },
  { value: "ultra" as const, label: "超清", description: "最佳质量，较慢", emoji: "💎" },
];

export function SettingsPanel({ isOpen, onClose, params, onParamsChange }: SettingsPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // ESC 关闭 - 只在面板打开时监听
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // 点击外部关闭 - 只在面板打开时监听
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div className={styles.overlay} />

      {/* 面板 */}
      <div ref={panelRef} className={styles.panel} role="dialog" aria-label="生成参数设置">
        {/* 头部 */}
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <EmojiIcon emoji="⚙️" color="mint" size="sm" />
            <h2>生成设置</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭设置"
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
              <h3>分辨率</h3>
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
              <h3>视频时长</h3>
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
                    {opt.emoji} {opt.label}
                  </div>
                  <div className={styles.optionDescription}>{opt.description}</div>
                </button>
              ))}
            </div>
          </section>

          {/* 风格 */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <EmojiIcon emoji="🎨" color="pink" size="xs" />
              <h3>画面风格</h3>
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
                    {opt.label}
                  </div>
                </button>
              ))}
            </div>
          </section>

          {/* 质量 */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <EmojiIcon emoji="💎" color="lavender" size="xs" />
              <h3>生成质量</h3>
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
                      {opt.emoji} {opt.label}
                    </div>
                    <div className={styles.qualityDescription}>{opt.description}</div>
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
