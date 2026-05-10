---
name: material-you
description: >
  将 Material You / Material Design 3 指南应用到 Android UI design、review 和 implementation。
  当用户询问 M3、dynamic color、Monet、Android theming、tonal palettes、color roles、
  Jetpack Compose theming、AOSP color APIs、adaptive layouts、accessibility，或任何 Android screen、component、app UI 工作时应使用此 skill。
license: MIT
---

# Material You Design Skill

Material You 是 Google 强调用户表达的 design language。核心理念是：color 不再只由 brand 决定，而是来自**用户的 wallpaper 或选择的 seed color**，并自动生成一套完整且满足 accessibility 要求的 palette。

## 核心概念速览

| Concept | Key Fact |
|---|---|
| Source | 1 个 seed color（CAM16 chroma ≥ 5） |
| Expansion | 5 个 tonal palettes × 13 个 tones = **65 个 color APIs** |
| Palette names | accent1、accent2、accent3、neutral1、neutral2 |
| Theme styles | TONAL_SPOT（默认）、EXPRESSIVE、VIBRANT、RAINBOW、FRUIT_SALAD、CONTENT |
| Typography | display、headline、title、body、label，每类都有 large/medium/small |
| Shape scale | extraSmall → extraLarge（corner radii 使用 dp） |
| Grid | 所有 spacing 和 sizing 使用 8dp base unit |
| Min touch target | 48×48dp |
| Min contrast | 标准文本 4.5:1（WCAG AA） |

---

## 1. Dynamic Color System（AOSP）

### 工作原理

```
User wallpaper / preset → seed color extraction（ColorScheme#getSeedColors）
         ↓
  Single source color（CAM16 chroma ≥ 5，default fallback: #1B6EF3）
         ↓
  通过 CAM16 hue/chroma rules 生成 5 个 tonal palettes：
    accent1  – primary hue, high chroma
    accent2  – primary hue, lower chroma
    accent3  – hue rotated +60°, medium chroma
    neutral1 – primary hue, chroma ≈ 4  (backgrounds)
    neutral2 – primary hue, chroma ≈ 8  (surfaces)
         ↓
  每个 palette 13 个 tones（luminance 0–1000）= 65 个 color attributes
  例如 R.color.system_accent1_10、system_neutral2_500
```

### Theme Style Selection（Android 13+）

通过 `Settings.Secure.THEME_CUSTOMIZATION_OVERLAY_PACKAGES` 设置：
```json
{
  "android.theme.customization.system_palette": "746BC1",
  "android.theme.customization.theme_style": "EXPRESSIVE"
}
```

**Theme styles 及其特性：**
- `TONAL_SPOT` – 中等 vibrancy，accent3 与 accent1 类似（Android 12 延续而来）
- `VIBRANT` – high chroma accents
- `EXPRESSIVE` – hue range 更广，palette spread 更具表现力
- `RAINBOW` – hue-spread across all palettes
- `FRUIT_SALAD` – multi-hue accent system
- `CONTENT` – low chroma，content-forward

> OEM 不强制要求在 UI 中暴露所有 styles，但 dynamic color palettes 必须通过这些 styles 之一生成
> （CTS 强制：`SystemPaletteTest#testThemeStyles`）。

### Non-Dynamic Fallback

对于不支持 wallpaper color extraction 的设备，禁用 dynamic picker 并使用默认 Material palette。这样可确保 Google apps 和兼容 M3 的第三方 apps 仍然有良好的视觉效果。

---

## 2. Color Roles（Material 3）

M3 会将 65 个 raw tonal colors 映射到 components 使用的**semantic color roles**：

| Role | Usage |
|---|---|
| `primary` / `onPrimary` | 关键 actions、FAB、active states |
| `primaryContainer` / `onPrimaryContainer` | selected chips、active nav items |
| `secondary` / `onSecondary` | supporting accents、filters |
| `secondaryContainer` / `onSecondaryContainer` | tonal chips、badges |
| `tertiary` / `onTertiary` | complementary accent（accent3 family） |
| `error` / `onError` | error states |
| `surface` / `onSurface` | cards、sheets、dialogs |
| `surfaceVariant` / `onSurfaceVariant` | input fields、icon containers |
| `outline` | input borders、dividers |
| `background` / `onBackground` | app background |

**Surface elevation tinting**（在 M3 中替代 shadows）：更高 elevation 的 surfaces 会叠加 primary-color tint（tone overlay）。避免 heavy drop shadows。

---

## 3. Typography Scale

将所有文本对齐到 **4dp baseline grid**。默认 typeface：**Roboto / Google Sans**。

| Token | Usage | Default Size |
|---|---|---|
| `displayLarge` | Hero text、splash | 57sp |
| `displayMedium` | | 45sp |
| `displaySmall` | | 36sp |
| `headlineLarge` | Page titles | 32sp |
| `headlineMedium` | | 28sp |
| `headlineSmall` | | 24sp |
| `titleLarge` | App bar、dialog titles | 22sp |
| `titleMedium` | List section headers | 16sp（medium weight） |
| `titleSmall` | | 14sp（medium weight） |
| `bodyLarge` | Primary body text | 16sp |
| `bodyMedium` | | 14sp |
| `bodySmall` | Captions | 12sp |
| `labelLarge` | Buttons | 14sp（medium weight） |
| `labelMedium` | Chips、tabs | 12sp |
| `labelSmall` | Badges | 11sp |

- 始终使用 `sp`（不要使用 `dp`）作为 font sizes，以尊重用户的 font-size preferences
- Body text 最小为 **14sp**；可读内容不要低于该尺寸
- Line height：font size 的 1.3–1.6 倍

---

## 4. Shape System

Shapes 用于传达 component identity 和 state。使用 M3 shape scale：

| Token | Corner Radius | Typical Components |
|---|---|---|
| `extraSmall` | 4dp | Tooltips、snackbars |
| `small` | 8dp | Chips、small cards |
| `medium` | 12dp | Cards、menus |
| `large` | 16dp | Dialogs、bottom sheets（top corners） |
| `extraLarge` | 24dp+ | FAB、large modal sheets |
| `full` | 50%（pill） | Buttons、extended FAB |

Shapes 也传达 state：fully rounded = interactive/selected；square = inactive/informational。

---

## 5. Elevation & Surfaces

M3 使用 **tonal elevation**（color overlay，不是 shadow）替代 shadow-heavy elevation：

- Level 0（surface）→ no tint
- Level 1 → +5% primary overlay
- Level 2 → +8%
- Level 3 → +11%（例如 FAB resting）
- Level 4 → +12%
- Level 5 → +14%

谨慎使用 shadows；将它们保留给 dialogs 和 menus 等 overlaid surfaces。

---

## 6. Motion Principles

**Responsive**：animations 在 interaction point 立即触发。  
**Natural**：movement 沿 arcs，使用 physics-based spring curves，而不是 linear。  
**Aware**：elements 会响应 nearby elements 和 user intent。  
**Intentional**：animation 引导 focus 并传达 hierarchy。

**Timing guidance：**
- Micro-interactions（tap feedback、ripples）：40–150ms
- State transitions（expand、collapse）：150–300ms
- Page/screen transitions：300–500ms（使用 shared element + container transforms）
- 大多数 animations 保持在 **300ms 以下**，以获得 snappy 的体验

**M3 transition patterns：**
- **Container transform** – shared element expansion（例如 card → detail）
- **Shared axis** – forward/backward navigation（horizontal、vertical 或 z-axis）
- **Fade through** – unrelated content swaps
- **Fade** – elements independently entering/exiting

---

## 7. Layout & Spacing

Base unit：**8dp**。所有 padding、margin 和 component sizing 都应为 8dp 的倍数（fine-grained adjustments 可使用 4dp）。

**Canonical adaptive layouts（M3）：**
- **List-detail** – 大屏上的 master list + detail panel
- **Supporting pane** – primary content + contextual sidebar
- **Feed** – responsive grid/column layout

**Navigation by screen size：**
- Phone（< 600dp）：Bottom navigation bar（3–5 destinations）
- Tablet / foldable（≥ 600dp）：Navigation rail（left side）
- Desktop / large（≥ 1240dp）：Navigation drawer（persistent）

**Touch targets：**所有 interactive elements 最小 **48×48dp**。可以通过 padding 扩展 hit area，而不改变 visual size。

---

## 8. Accessibility Requirements

- **Color contrast**：normal text ≥ 4.5:1（WCAG AA）；large text（18sp+）≥ 3:1
- **不要只依赖 color** 传达含义，也要使用 icons、labels 或 patterns
- 所有 custom interactive components 都需要 `contentDescription`
- 支持 `android:textAppearance`，以适配 system font scaling
- Line length：40–80 个字符，以保证 readability

---

## 9. Compose Implementation

```kotlin
// Enable dynamic color (Android 12+)
@Composable
fun AppTheme(
    useDarkTheme: Boolean = isSystemInDarkTheme(),
    useDynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        useDynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            if (useDarkTheme) dynamicDarkColorScheme(LocalContext.current)
            else dynamicLightColorScheme(LocalContext.current)
        }
        useDarkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        shapes = AppShapes,
        content = content
    )
}

// Custom shape scale
val AppShapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small      = RoundedCornerShape(8.dp),
    medium     = RoundedCornerShape(12.dp),
    large      = RoundedCornerShape(16.dp),
    extraLarge = RoundedCornerShape(24.dp)
)

// Use semantic color roles — never hardcode hex values in production
Text(
    text = "Hello",
    color = MaterialTheme.colorScheme.onSurface,
    style = MaterialTheme.typography.bodyLarge
)
```

### Compose 关键规则
- 始终使用 **semantic color roles**（使用 `colorScheme.primary`，不要使用 `Color(0xFF6750A4)`）
- 使用 `isSystemInDarkTheme()` 自动切换 color schemes
- 为 accessibility 使用 `Modifier.semantics { contentDescription = "..." }`
- 使用 `animateContentSize()`、`AnimatedVisibility` 和 Compose built-in transitions

---

## 10. XML / View System

```xml
<!-- Theme declaration -->
<style name="Theme.MyApp" parent="Theme.Material3.DayNight">
    <item name="colorPrimary">@color/md_theme_primary</item>
    <item name="colorOnPrimary">@color/md_theme_onPrimary</item>
    <item name="colorSecondary">@color/md_theme_secondary</item>
    <!-- Use Material3 tokens — never override with raw hex in production -->
</style>

<!-- Button following M3 -->
<com.google.android.material.button.MaterialButton
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"
    android:text="Action"
    style="@style/Widget.Material3.Button" />
```

---

## 11. Quick Design Checklist

使用 Material You review 或构建 Android UI 时，确认：

- [ ] Dynamic color enabled（API 31+），并提供 static fallback
- [ ] 所有 colors 都引用 semantic tokens，而不是 hardcoded hex
- [ ] Typography 使用 M3 type scale，并使用 `sp` units
- [ ] Shapes 遵循 4/8/12/16/24dp scale
- [ ] Elevation 使用 tonal overlay，而不是 heavy shadows
- [ ] Touch targets ≥ 48×48dp
- [ ] Contrast ratios ≥ 4.5:1
- [ ] 所有 spacings 都是 8dp 的倍数（或 4dp fine-grained）
- [ ] Navigation 随 screen width 自适应（bottom bar → rail → drawer）
- [ ] 标准 transitions 低于 300ms
- [ ] 支持 dark theme（通过 `DayNight` / `isSystemInDarkTheme` 自动切换）

---

## Reference Links

- AOSP Material You: https://source.android.com/docs/core/display/material  
- AOSP Dynamic Color: https://source.android.com/docs/core/display/dynamic-color  
- Material Design 3: https://m3.material.io  
- Compose M3: https://developer.android.com/develop/ui/compose/designsystems/material3
