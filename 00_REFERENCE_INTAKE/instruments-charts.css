/* @ds-bundle: {"format":4,"namespace":"AISMATCommandDeck_f4ddd5","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"StatusChip","sourcePath":"components/core/StatusChip.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"CaveatBanner","sourcePath":"components/feedback/CaveatBanner.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/feedback/Tooltip.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Radio","sourcePath":"components/forms/Radio.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"CitationChip","sourcePath":"components/instruments/CitationChip.jsx"},{"name":"DcmaStrip","sourcePath":"components/instruments/DcmaStrip.jsx"},{"name":"GanttChart","sourcePath":"components/instruments/GanttChart.jsx"},{"name":"InstrumentPanel","sourcePath":"components/instruments/InstrumentPanel.jsx"},{"name":"MetricTile","sourcePath":"components/instruments/MetricTile.jsx"},{"name":"ProgramTile","sourcePath":"components/instruments/ProgramTile.jsx"},{"name":"Sparkline","sourcePath":"components/instruments/Sparkline.jsx"},{"name":"TrendChart","sourcePath":"components/instruments/TrendChart.jsx"},{"name":"AirGapIndicator","sourcePath":"components/navigation/AirGapIndicator.jsx"},{"name":"RoleStrip","sourcePath":"components/navigation/RoleStrip.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"a7989afe35e3","components/core/Button.jsx":"815753ef640b","components/core/Icon.jsx":"b258b83157dd","components/core/IconButton.jsx":"45863a50e5a3","components/core/StatusChip.jsx":"291c82fd72f7","components/core/Tag.jsx":"60d198e28b39","components/feedback/CaveatBanner.jsx":"292f2945d610","components/feedback/Dialog.jsx":"a68e385ca0d7","components/feedback/Toast.jsx":"b947cce16dfe","components/feedback/Tooltip.jsx":"938290bf7a2a","components/forms/Checkbox.jsx":"3b6894336a09","components/forms/Input.jsx":"b9388252e831","components/forms/Radio.jsx":"c3fa39d81264","components/forms/Select.jsx":"9ab61b2e74d9","components/forms/Switch.jsx":"a3b4166822df","components/instruments/CitationChip.jsx":"5aa798c2b47e","components/instruments/DcmaStrip.jsx":"4d7e63d3b5ad","components/instruments/GanttChart.jsx":"1293310e2946","components/instruments/InstrumentPanel.jsx":"50d3557393e1","components/instruments/MetricTile.jsx":"fd73d002a43c","components/instruments/ProgramTile.jsx":"e657e455eac6","components/instruments/Sparkline.jsx":"17462b86adc3","components/instruments/TrendChart.jsx":"e31ef8c30d11","components/navigation/AirGapIndicator.jsx":"41839ba8b553","components/navigation/RoleStrip.jsx":"a6431068567a","components/navigation/Tabs.jsx":"6464c22ffa32","ui_kits/aismat/ActCompliance.jsx":"f72c48aeea97","ui_kits/aismat/ActDataRoom.jsx":"5175a35bca79","ui_kits/aismat/ActDeepDive.jsx":"416478e90dbc","ui_kits/aismat/ActIngest.jsx":"b185171096ee","ui_kits/aismat/ActLedger.jsx":"116cc2a34a6c","ui_kits/aismat/ActOrbit.jsx":"89fc3a1f7d1e","ui_kits/aismat/ActPortfolio.jsx":"45f74e4042f2","ui_kits/aismat/ActRisk.jsx":"ac181f2b0f1e","ui_kits/aismat/DeepDiveEVM.jsx":"4ba69030097c","ui_kits/aismat/DeepDiveForensics.jsx":"abf7ac1c1f34","ui_kits/aismat/DeepDiveQuality.jsx":"c2b4bb22653e","ui_kits/aismat/KitBits.jsx":"ec11f7978d9d","ui_kits/aismat/Shell.jsx":"2c607f57d287","ui_kits/aismat/Tour.jsx":"b80825e5c75b","ui_kits/aismat/data.js":"c919f1cbbc4c"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.AISMATCommandDeck_f4ddd5 = window.AISMATCommandDeck_f4ddd5 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function toKebab(s) {
  return String(s).replace(/([a-z0-9])([A-Z])/g, "$1-$2").replace(/\s+/g, "-").toLowerCase();
}

/**
 * Icon — thin wrapper over Lucide. The page must have the Lucide UMD script
 * loaded (all AISMAT cards / kits do). Renders an inline <svg> that inherits
 * currentColor, so an icon takes the color of its surrounding text token.
 */
function Icon({
  name,
  size = 18,
  strokeWidth = 2,
  className = "",
  style = {},
  label,
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.innerHTML = "";
    const i = document.createElement("i");
    i.setAttribute("data-lucide", toKebab(name));
    el.appendChild(i);
    const L = typeof window !== "undefined" && window.lucide;
    if (L && L.createIcons) {
      try {
        L.createIcons();
      } catch (e) {/* noop */}
      const svg = el.querySelector("svg");
      if (svg) {
        svg.setAttribute("width", size);
        svg.setAttribute("height", size);
        svg.setAttribute("stroke-width", strokeWidth);
      }
    }
  }, [name, size, strokeWidth]);
  return /*#__PURE__*/React.createElement("span", _extends({
    ref: ref,
    className: "aismat-icon " + className,
    role: label ? "img" : undefined,
    "aria-label": label || undefined,
    "aria-hidden": label ? undefined : true,
    style: {
      width: size,
      height: size,
      ...style
    }
  }, rest));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Badge — small mono count / label chip. Neutral by default; accent or gold
 * for emphasis. For RAG health status use StatusChip instead.
 */
function Badge({
  tone = "neutral",
  icon,
  children,
  className = "",
  ...rest
}) {
  const cls = ["aismat-badge", tone !== "neutral" ? "aismat-badge--" + tone : "", className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 12
  }) : null, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Button — primary action control. Variants map to intent: primary (cyan) for
 * the one main action, secondary for supporting actions, ghost for low-emphasis
 * / toolbar text actions, danger for destructive.
 */
function Button({
  variant = "primary",
  size = "md",
  iconLeft,
  iconRight,
  fullWidth = false,
  disabled = false,
  type = "button",
  className = "",
  children,
  ...rest
}) {
  const cls = ["aismat-btn", "aismat-btn--" + variant, "aismat-btn--" + size, fullWidth ? "aismat-btn--full" : "", className].filter(Boolean).join(" ");
  const isize = size === "lg" ? 18 : size === "sm" ? 14 : 16;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    className: cls,
    disabled: disabled
  }, rest), iconLeft ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconLeft,
    size: isize
  }) : null, children != null ? /*#__PURE__*/React.createElement("span", null, children) : null, iconRight ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconRight,
    size: isize
  }) : null);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * IconButton — square icon-only control for dense toolbars (grid / download /
 * expand). Always pass `label` (used as accessible name + native tooltip).
 */
function IconButton({
  icon,
  size = "md",
  active = false,
  label,
  className = "",
  ...rest
}) {
  const cls = ["aismat-iconbtn", "aismat-iconbtn--" + size, active ? "aismat-iconbtn--active" : "", className].filter(Boolean).join(" ");
  const isize = size === "sm" ? 15 : size === "lg" ? 20 : 17;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    className: cls,
    "aria-label": label,
    title: label,
    "aria-pressed": active
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: isize
  }));
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/StatusChip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const DEFAULT_LABELS = {
  pass: "Pass",
  warn: "Watch",
  fail: "Fail",
  info: "Info",
  driving: "Driving",
  neutral: "—"
};

/**
 * StatusChip — RAG health indicator that carries a text label AND a dot, so
 * status survives color-blindness and grayscale print (never color alone).
 */
function StatusChip({
  status = "neutral",
  children,
  showDot = true,
  className = "",
  ...rest
}) {
  const label = children != null ? children : DEFAULT_LABELS[status];
  const cls = ["aismat-statuschip", "aismat-statuschip--" + status, className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), showDot ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-statuschip__dot"
  }) : null, label);
}
Object.assign(__ds_scope, { StatusChip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/StatusChip.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Tag — a filter / attribute chip, optionally removable. Used in the Portfolio
 * filter bar and saved-view chips.
 */
function Tag({
  children,
  onRemove,
  icon,
  className = "",
  ...rest
}) {
  const cls = ["aismat-tag", className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("span", _extends({
    className: cls
  }, rest), icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 13
  }) : null, /*#__PURE__*/React.createElement("span", null, children), onRemove ? /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "aismat-tag__x",
    "aria-label": "Remove filter",
    onClick: onRemove
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 13
  })) : null);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/feedback/CaveatBanner.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const CI = {
  warn: "triangle-alert",
  fail: "circle-alert",
  info: "info"
};

/**
 * CaveatBanner — surfaces a metric caveat (e.g. a SUSPECTED engine flag) in
 * plain sight. Load-bearing UI: the tool never hides uncertainty behind a
 * clean number, so this sits inline with the flagged metric.
 */
function CaveatBanner({
  status = "warn",
  title = "SUSPECTED",
  children,
  icon,
  className = "",
  ...rest
}) {
  const cls = ["aismat-caveat", "aismat-caveat--" + status, className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    role: "note"
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "aismat-caveat__icon"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon || CI[status],
    size: 17
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "aismat-caveat__title"
  }, title), children ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-caveat__text"
  }, children) : null));
}
Object.assign(__ds_scope, { CaveatBanner });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/CaveatBanner.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
/**
 * Dialog — modal over a blurred scrim. Closes on Escape, close button, and
 * scrim click. Pass `footer` (usually Buttons) for actions.
 */
function Dialog({
  open,
  onClose,
  title,
  subtitle,
  footer,
  className = "",
  children
}) {
  React.useEffect(() => {
    if (!open) return;
    const onKey = e => {
      if (e.key === "Escape" && onClose) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "aismat-dialog__scrim",
    onMouseDown: e => {
      if (e.target === e.currentTarget && onClose) onClose();
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "aismat-dialog " + className,
    role: "dialog",
    "aria-modal": "true"
  }, /*#__PURE__*/React.createElement("div", {
    className: "aismat-dialog__head"
  }, /*#__PURE__*/React.createElement("div", null, title ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-dialog__title"
  }, title) : null, subtitle ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-dialog__sub"
  }, subtitle) : null), onClose ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Close",
    onClick: onClose
  }) : null), /*#__PURE__*/React.createElement("div", {
    className: "aismat-dialog__body"
  }, children), footer ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-dialog__foot"
  }, footer) : null));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const ICONS = {
  pass: "circle-check",
  warn: "triangle-alert",
  fail: "circle-alert",
  info: "info"
};

/**
 * Toast — transient status notification. Presentational; a host app supplies a
 * corner stack and auto-dismiss timing.
 */
function Toast({
  status = "info",
  title,
  children,
  onClose,
  icon,
  className = "",
  ...rest
}) {
  const cls = ["aismat-toast", "aismat-toast--" + status, className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("div", _extends({
    className: cls,
    role: "status"
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "aismat-toast__icon"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon || ICONS[status],
    size: 16
  })), /*#__PURE__*/React.createElement("div", {
    className: "aismat-toast__body"
  }, title ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-toast__title"
  }, title) : null, children ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-toast__msg"
  }, children) : null), onClose ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Dismiss",
    size: "sm",
    onClick: onClose
  }) : null);
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tooltip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Tooltip — the AISMAT hover-to-explain callout. Appears after a dwell (~0.7s),
 * the highest-leverage teaching surface in the product. Pass free-form
 * `content`, OR the structured what/how/example trio (what it is → how it is
 * computed → a worked example of how to act on it).
 */
function Tooltip({
  content,
  what,
  how,
  example,
  placement = "top",
  dwell = 700,
  className = "",
  children,
  ...rest
}) {
  const [open, setOpen] = React.useState(false);
  const timer = React.useRef(null);
  const show = () => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setOpen(true), dwell);
  };
  const hide = () => {
    clearTimeout(timer.current);
    setOpen(false);
  };
  React.useEffect(() => () => clearTimeout(timer.current), []);
  const popCls = ["aismat-tt__pop", "aismat-tt__pop--" + placement, open ? "aismat-tt__pop--open" : ""].join(" ");
  const body = content != null ? content : /*#__PURE__*/React.createElement(React.Fragment, null, what ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-explain__what"
  }, what) : null, how ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-explain__how"
  }, how) : null, example ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-explain__eg"
  }, example) : null);
  return /*#__PURE__*/React.createElement("span", _extends({
    className: "aismat-tt " + className,
    onMouseEnter: show,
    onMouseLeave: hide,
    onFocus: show,
    onBlur: hide
  }, rest), children, /*#__PURE__*/React.createElement("span", {
    className: popCls,
    role: "tooltip"
  }, body));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Checkbox — custom-styled control with a Lucide check glyph. */
function Checkbox({
  label,
  disabled = false,
  className = "",
  ...rest
}) {
  const cls = ["aismat-check", disabled ? "aismat-check--disabled" : "", className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("label", {
    className: cls
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "checkbox",
    className: "aismat-check__input",
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "aismat-check__box"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "check",
    size: 13,
    strokeWidth: 3
  })), label != null ? /*#__PURE__*/React.createElement("span", null, label) : null);
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Input — text field with optional label, hint, error, and a leading icon.
 * Use `mono` for numeric / ID entry so digits align with data readouts.
 */
function Input({
  label,
  hint,
  error,
  prefixIcon,
  mono = false,
  size = "md",
  required = false,
  id,
  className = "",
  ...rest
}) {
  const autoId = React.useId();
  const inputId = id || autoId;
  const inputCls = ["aismat-input", size === "sm" ? "aismat-input--sm" : "", mono ? "aismat-input--mono" : "", prefixIcon ? "aismat-input--haspre" : "", error ? "aismat-input--invalid" : "", className].filter(Boolean).join(" ");
  const control = /*#__PURE__*/React.createElement("div", {
    className: "aismat-inputwrap"
  }, prefixIcon ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-inputwrap__icon"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: prefixIcon,
    size: 16
  })) : null, /*#__PURE__*/React.createElement("input", _extends({
    id: inputId,
    className: inputCls,
    "aria-invalid": error ? true : undefined
  }, rest)));
  if (!label && !hint && !error) return control;
  return /*#__PURE__*/React.createElement("div", {
    className: "aismat-field"
  }, label ? /*#__PURE__*/React.createElement("label", {
    className: "aismat-label",
    htmlFor: inputId
  }, label, required ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-label__req"
  }, "*") : null) : null, control, error ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-hint aismat-hint--error"
  }, error) : hint ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-hint"
  }, hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Radio.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Radio — single-choice control. Group by shared `name`. */
function Radio({
  label,
  disabled = false,
  className = "",
  ...rest
}) {
  const cls = ["aismat-radio", disabled ? "aismat-radio--disabled" : "", className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("label", {
    className: cls
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "radio",
    className: "aismat-radio__input",
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "aismat-radio__box"
  }), label != null ? /*#__PURE__*/React.createElement("span", null, label) : null);
}
Object.assign(__ds_scope, { Radio });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Radio.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Select — native select styled as an AISMAT control, with a chevron. Pass
 * `options` (strings or {value,label}) or your own <option> children.
 */
function Select({
  label,
  hint,
  error,
  options = [],
  size = "md",
  id,
  className = "",
  children,
  ...rest
}) {
  const autoId = React.useId();
  const selId = id || autoId;
  const cls = ["aismat-select", size === "sm" ? "aismat-select--sm" : "", className].filter(Boolean).join(" ");
  const control = /*#__PURE__*/React.createElement("div", {
    className: "aismat-selectwrap"
  }, /*#__PURE__*/React.createElement("select", _extends({
    id: selId,
    className: cls
  }, rest), children ? children : options.map(o => {
    const val = typeof o === "string" ? o : o.value;
    const lab = typeof o === "string" ? o : o.label;
    return /*#__PURE__*/React.createElement("option", {
      key: val,
      value: val
    }, lab);
  })), /*#__PURE__*/React.createElement("span", {
    className: "aismat-selectwrap__chev"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 16
  })));
  if (!label && !hint && !error) return control;
  return /*#__PURE__*/React.createElement("div", {
    className: "aismat-field"
  }, label ? /*#__PURE__*/React.createElement("label", {
    className: "aismat-label",
    htmlFor: selId
  }, label) : null, control, error ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-hint aismat-hint--error"
  }, error) : hint ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-hint"
  }, hint) : null);
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Switch — on/off toggle for settings and view options (e.g. reduce motion). */
function Switch({
  label,
  disabled = false,
  className = "",
  ...rest
}) {
  const cls = ["aismat-switch", disabled ? "aismat-switch--disabled" : "", className].filter(Boolean).join(" ");
  return /*#__PURE__*/React.createElement("label", {
    className: cls
  }, /*#__PURE__*/React.createElement("input", _extends({
    type: "checkbox",
    role: "switch",
    className: "aismat-switch__input",
    disabled: disabled
  }, rest)), /*#__PURE__*/React.createElement("span", {
    className: "aismat-switch__track"
  }, /*#__PURE__*/React.createElement("span", {
    className: "aismat-switch__thumb"
  })), label != null ? /*#__PURE__*/React.createElement("span", null, label) : null);
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/instruments/CitationChip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * CitationChip — a click-through to a fact in the ledger. Every AI-generated
 * sentence and every metric renders its supporting fact IDs as these, so a
 * user can always reach the raw data behind a claim. Warn-toned when the fact
 * is itself SUSPECTED.
 */
function CitationChip({
  id,
  confirmed = true,
  onClick,
  className = "",
  ...rest
}) {
  const cls = ["aismat-cite", confirmed ? "" : "aismat-cite--suspected", className].filter(Boolean).join(" ");
  const text = String(id).startsWith("#") ? id : "#" + id;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    className: cls,
    onClick: onClick
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: confirmed ? "file-search" : "triangle-alert",
    size: 11
  }), text);
}
Object.assign(__ds_scope, { CitationChip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/CitationChip.jsx", error: String((e && e.message) || e) }); }

// components/instruments/DcmaStrip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * DcmaStrip — the DCMA-14 pass/fail strip: 14 compact cells, green pass / red
 * fail / amber warn / grey n-a, numbered by check. Native title shows the
 * check name on hover; pair with a summary count ("11/14 pass") beside it.
 */
function DcmaStrip({
  results = [],
  showIndex = true,
  className = "",
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    className: "aismat-dcma " + className
  }, rest), results.map((r, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    className: "aismat-dcma__cell aismat-dcma__cell--" + (r.status || "na"),
    title: r.name
  }, showIndex ? i + 1 : "")));
}
Object.assign(__ds_scope, { DcmaStrip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/DcmaStrip.jsx", error: String((e && e.message) || e) }); }

// components/instruments/GanttChart.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Opt({
  on,
  onClick,
  icon,
  children
}) {
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "aismat-chartopt" + (on ? " aismat-chartopt--on" : ""),
    "aria-pressed": on,
    onClick: onClick
  }, icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 12
  }) : null, children);
}

/**
 * GanttChart — THE standardized schedule bar chart. Every Gantt in AISMAT
 * renders through this component so the format is identical everywhere:
 * same three columns (activity | track | TF), same colors (gold = driving/
 * critical, neutral = non-critical, dashed = free float), and the same
 * options strip in the same place (Float · Driving · Walk · Baseline).
 * Specialized tabs pass `extraOptions` — appended to the SAME strip.
 * Every float value carries the standard hover-to-explain tooltip.
 */
function GanttChart({
  activities = [],
  phase = "current",
  dataDate = null,
  extraOptions = null,
  walkable = true,
  defaultFloat = true,
  defaultDriving = true,
  defaultBaseline = false,
  lowFloatBadge = null,
  note = null,
  className = "",
  ...rest
}) {
  const [showFloat, setShowFloat] = React.useState(defaultFloat);
  const [driving, setDriving] = React.useState(defaultDriving);
  const [walk, setWalk] = React.useState(false);
  const hasBase = activities.some(a => a.baseline);
  const [showBase, setShowBase] = React.useState(defaultBaseline);
  const [flash, setFlash] = React.useState(false);
  const first = React.useRef(true);
  React.useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    setFlash(true);
    const t = setTimeout(() => setFlash(false), 950);
    return () => clearTimeout(t);
  }, [phase]);
  const total = Math.max(1, ...activities.map(a => Math.max(a.s + a.d, a.baseline ? a.baseline.s + a.baseline.d : 0, a.s + a.d + (a.tf > 0 ? a.tf : 0))));
  const pct = v => v / total * 100 + "%";
  let minTf = Infinity,
    minIdx = -1;
  activities.forEach((a, i) => {
    if (a.tf < minTf) {
      minTf = a.tf;
      minIdx = i;
    }
  });
  let critSeq = 0;
  return /*#__PURE__*/React.createElement("div", _extends({
    className: "aismat-gantt-wrap " + className
  }, rest), /*#__PURE__*/React.createElement("div", {
    className: "aismat-chartopts"
  }, /*#__PURE__*/React.createElement(Opt, {
    on: showFloat,
    onClick: () => setShowFloat(!showFloat),
    icon: "ruler"
  }, "Float"), /*#__PURE__*/React.createElement(Opt, {
    on: driving,
    onClick: () => setDriving(!driving),
    icon: "zap"
  }, "Driving"), walkable ? /*#__PURE__*/React.createElement(Opt, {
    on: walk,
    onClick: () => setWalk(!walk),
    icon: "footprints"
  }, "Walk path") : null, hasBase ? /*#__PURE__*/React.createElement(Opt, {
    on: showBase,
    onClick: () => setShowBase(!showBase),
    icon: "ghost"
  }, "Baseline") : null, extraOptions, note ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-chartnote"
  }, note) : null), /*#__PURE__*/React.createElement("div", {
    className: "aismat-gantt"
  }, activities.map((a, i) => {
    const g = phase === "baseline" && a.baseline ? a.baseline : {
      s: a.s,
      d: a.d
    };
    const changed = a.baseline && (a.baseline.s !== a.s || a.baseline.d !== a.d);
    const wi = a.crit ? critSeq++ : 0;
    const barCls = ["aismat-gantt__bar", a.crit && driving ? "aismat-gantt__bar--crit" : "", showBase && a.baseline ? "aismat-gantt__bar--slim" : "", walk && a.crit && driving ? "aismat-gantt__bar--walk" : "", flash && changed ? "aismat-gantt__bar--changed" : ""].filter(Boolean).join(" ");
    const name = /*#__PURE__*/React.createElement("span", {
      className: "aismat-gantt__name"
    }, a.name);
    const tfCls = "aismat-gantt__tf" + (a.tf < 0 ? " aismat-gantt__tf--neg" : a.crit ? " aismat-gantt__tf--crit" : "");
    const tfEl = /*#__PURE__*/React.createElement("span", {
      className: tfCls
    }, a.tf, "d");
    return /*#__PURE__*/React.createElement("div", {
      className: "aismat-gantt__row",
      key: a.id || i
    }, lowFloatBadge && i === minIdx ? /*#__PURE__*/React.createElement(__ds_scope.Tooltip, {
      dwell: 1200,
      placement: "right",
      content: lowFloatBadge
    }, name) : name, /*#__PURE__*/React.createElement("div", {
      className: "aismat-gantt__track"
    }, dataDate != null ? /*#__PURE__*/React.createElement("span", {
      className: "aismat-gantt__dd",
      style: {
        left: pct(dataDate)
      }
    }) : null, showBase && a.baseline ? /*#__PURE__*/React.createElement("span", {
      className: "aismat-gantt__ghost",
      style: {
        left: pct(a.baseline.s),
        width: pct(a.baseline.d)
      }
    }) : null, /*#__PURE__*/React.createElement("div", {
      className: barCls,
      style: {
        left: pct(g.s),
        width: pct(g.d),
        animationDelay: walk && a.crit ? wi * 0.45 + "s" : undefined
      }
    }), showFloat && a.tf > 0 ? /*#__PURE__*/React.createElement("div", {
      className: "aismat-gantt__float",
      style: {
        left: pct(g.s + g.d),
        width: pct(a.tf)
      }
    }) : null), a.tf > 0 ? /*#__PURE__*/React.createElement(__ds_scope.Tooltip, {
      placement: "left",
      what: a.tf + " days of total float.",
      how: "Late finish \u2212 early finish for this activity, from the current CPM run.",
      example: "It can slip " + a.tf + " workdays before it eats into the critical path — watch it if the upstream driving activity is already late."
    }, tfEl) : /*#__PURE__*/React.createElement(__ds_scope.Tooltip, {
      placement: "left",
      what: a.tf < 0 ? Math.abs(a.tf) + " days of negative float." : "Zero float — this activity is driving.",
      how: "Late finish \u2212 early finish, from the current CPM run.",
      example: a.tf < 0 ? "It is already " + Math.abs(a.tf) + " workdays behind the network — recovery or re-baseline required." : "Any slip here moves the project finish day-for-day."
    }, tfEl));
  })));
}
Object.assign(__ds_scope, { GanttChart });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/GanttChart.jsx", error: String((e && e.message) || e) }); }

// components/instruments/InstrumentPanel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * InstrumentPanel — the AISMAT chart frame. Encodes the doctrine: a plain-
 * English takeaway headline, the visual, and a legend + toolbar. Every chart
 * in the product is wrapped in one of these; a chart without a takeaway does
 * not ship. The toolbar order is fixed everywhere: explain → grid → download
 * → expand.
 */
function InstrumentPanel({
  title,
  takeaway,
  flag,
  legend,
  toolbar,
  actions,
  onExplain,
  onGrid,
  onDownload,
  onExpand,
  className = "",
  children,
  ...rest
}) {
  const flagNode = flag ? typeof flag === "string" ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-flag aismat-flag--" + (/^conf/i.test(flag) ? "confirmed" : "suspected")
  }, flag) : flag : null;
  const defaultTools = /*#__PURE__*/React.createElement(React.Fragment, null, onExplain ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "circle-help",
    label: "How to read this",
    onClick: onExplain,
    size: "sm"
  }) : null, onGrid ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "grid-3x3",
    label: "Data grid",
    onClick: onGrid,
    size: "sm"
  }) : null, onDownload ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "download",
    label: "Export",
    onClick: onDownload,
    size: "sm"
  }) : null, onExpand ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "maximize-2",
    label: "Expand",
    onClick: onExpand,
    size: "sm"
  }) : null);
  const legendNode = Array.isArray(legend) ? legend.map((l, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    className: "aismat-legend__item"
  }, /*#__PURE__*/React.createElement("span", {
    className: "aismat-legend__swatch",
    style: {
      background: l.color
    }
  }), l.label)) : legend;
  return /*#__PURE__*/React.createElement("section", _extends({
    className: "aismat-panel " + className
  }, rest), /*#__PURE__*/React.createElement("div", {
    className: "aismat-panel__head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "aismat-panel__eyebrow"
  }, title, flagNode), /*#__PURE__*/React.createElement("div", {
    className: "aismat-panel__tools"
  }, toolbar !== undefined ? toolbar : defaultTools)), takeaway ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-panel__takeaway"
  }, takeaway) : null, /*#__PURE__*/React.createElement("div", {
    className: "aismat-panel__body"
  }, children), legend || actions ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-panel__foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "aismat-legend"
  }, legendNode), actions) : null);
}
Object.assign(__ds_scope, { InstrumentPanel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/InstrumentPanel.jsx", error: String((e && e.message) || e) }); }

// components/instruments/MetricTile.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * MetricTile — a single headline number (SPI, float, DCMA pass rate) with an
 * uppercase label, optional unit, a trend row, and a SUSPECTED/CONFIRMED flag.
 * Values are mono + tabular so tiles line up in a row.
 */
function MetricTile({
  label,
  value,
  unit,
  valueTone,
  trendDir,
  trendTone = "neutral",
  delta,
  flag,
  className = "",
  children,
  ...rest
}) {
  const arrow = trendDir === "up" ? "trending-up" : trendDir === "down" ? "trending-down" : trendDir === "flat" ? "minus" : null;
  const flagNode = flag ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-flag aismat-flag--" + (/^conf/i.test(flag) ? "confirmed" : "suspected")
  }, flag) : null;
  return /*#__PURE__*/React.createElement("div", _extends({
    className: "aismat-metric " + className
  }, rest), /*#__PURE__*/React.createElement("div", {
    className: "aismat-metric__label"
  }, /*#__PURE__*/React.createElement("span", null, label), flagNode), /*#__PURE__*/React.createElement("div", {
    className: "aismat-metric__value" + (valueTone ? " aismat-metric__value--" + valueTone : "")
  }, value, unit ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-metric__unit"
  }, unit) : null), delta != null || arrow ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-metric__trend aismat-metric__trend--" + trendTone
  }, arrow ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: arrow,
    size: 14
  }) : null, delta) : null, children);
}
Object.assign(__ds_scope, { MetricTile });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/MetricTile.jsx", error: String((e && e.message) || e) }); }

// components/instruments/ProgramTile.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * ProgramTile — a node in the Orbit "constellation". Colored + ringed by
 * health, pulses ONLY when its status changed since the last update (motion is
 * a signal). Renders as a button; wire onClick to zoom into the program.
 */
function ProgramTile({
  name,
  health = "neutral",
  metric,
  sub,
  trendDir,
  changed = false,
  onClick,
  className = "",
  ...rest
}) {
  const cls = ["aismat-progtile", "aismat-progtile--" + health, changed ? "aismat-progtile--changed" : "", className].filter(Boolean).join(" ");
  const arrow = trendDir === "up" ? "trending-up" : trendDir === "down" ? "trending-down" : null;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    className: cls,
    onClick: onClick
  }, rest), /*#__PURE__*/React.createElement("div", {
    className: "aismat-progtile__top"
  }, /*#__PURE__*/React.createElement("span", {
    className: "aismat-progtile__name"
  }, name), /*#__PURE__*/React.createElement("span", {
    className: "aismat-progtile__health aismat-progtile__health--" + health
  })), metric != null ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-progtile__metric"
  }, arrow ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: arrow,
    size: 17
  }) : null, metric) : null, sub ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-progtile__sub"
  }, sub) : null);
}
Object.assign(__ds_scope, { ProgramTile });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/ProgramTile.jsx", error: String((e && e.message) || e) }); }

// components/instruments/Sparkline.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Sparkline — inline SVG trend line for a small number series (SPI/CPI, float).
 * Draws left-to-right on load (trend reveal) unless animate is off. Pass a
 * --viz-* / status token as `color`.
 */
function Sparkline({
  data = [],
  width = 120,
  height = 32,
  color = "var(--accent)",
  strokeWidth = 2,
  fill = false,
  animate = true,
  className = "",
  ...rest
}) {
  const gid = React.useId().replace(/:/g, "");
  if (!data || data.length < 2) {
    return /*#__PURE__*/React.createElement("svg", _extends({
      className: "aismat-spark " + className,
      width: width,
      height: height
    }, rest));
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = strokeWidth + 1;
  const stepX = (width - pad * 2) / (data.length - 1);
  const pts = data.map((d, i) => {
    const x = pad + i * stepX;
    const y = pad + (1 - (d - min) / span) * (height - pad * 2);
    return [x, y];
  });
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  let len = 0;
  for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  len = Math.ceil(len) + 2;
  const base = (height - pad).toFixed(1);
  const area = fill ? "M" + pts[0][0].toFixed(1) + " " + base + " " + pts.map(p => "L" + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ") + " L" + pts[pts.length - 1][0].toFixed(1) + " " + base + " Z" : null;
  const lineStyle = animate ? {
    "--trend-length": len,
    strokeDasharray: len
  } : undefined;
  return /*#__PURE__*/React.createElement("svg", _extends({
    className: "aismat-spark " + className,
    width: width,
    height: height
  }, rest), fill ? /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("linearGradient", {
    id: "sg" + gid,
    x1: "0",
    y1: "0",
    x2: "0",
    y2: "1"
  }, /*#__PURE__*/React.createElement("stop", {
    offset: "0%",
    stopColor: color,
    stopOpacity: "0.22"
  }), /*#__PURE__*/React.createElement("stop", {
    offset: "100%",
    stopColor: color,
    stopOpacity: "0"
  }))) : null, fill ? /*#__PURE__*/React.createElement("path", {
    d: area,
    fill: "url(#sg" + gid + ")",
    stroke: "none"
  }) : null, /*#__PURE__*/React.createElement("path", {
    className: "aismat-spark__line" + (animate ? " aismat-spark__line--animate" : ""),
    d: line,
    stroke: color,
    strokeWidth: strokeWidth,
    style: lineStyle
  }));
}
Object.assign(__ds_scope, { Sparkline });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/Sparkline.jsx", error: String((e && e.message) || e) }); }

// components/instruments/TrendChart.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * TrendChart — THE standardized time-series instrument: metric(s) over
 * schedule updates, drawn left-to-right on load (trend reveal), with a fixed
 * grid, update labels, optional vertical markers / horizontal reference line,
 * and a hover crosshair with a mono readout. Use for every "metric over time"
 * view so trends read identically everywhere.
 */
function TrendChart({
  series = [],
  labels = [],
  height = 170,
  yMin,
  yMax,
  yFormat = v => String(v),
  markers = [],
  hline = null,
  animate = true,
  extraOptions = null,
  note = null,
  className = "",
  ...rest
}) {
  const [hov, setHov] = React.useState(null);
  const W = 560,
    P = {
      l: 38,
      r: 12,
      t: 12,
      b: 22
    };
  const H = height;
  const n = Math.max(labels.length, ...series.map(s => s.data.length), 2);
  const all = series.flatMap(s => s.data).concat(hline ? [hline.value] : []);
  const lo = yMin != null ? yMin : Math.min(...all);
  const hi = yMax != null ? yMax : Math.max(...all);
  const span = hi - lo || 1;
  const X = i => P.l + i / (n - 1) * (W - P.l - P.r);
  const Y = v => H - P.b - (v - lo) / span * (H - P.t - P.b);
  const onMove = e => {
    const r = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width * W;
    const i = Math.round((x - P.l) / (W - P.l - P.r) * (n - 1));
    setHov(Math.max(0, Math.min(n - 1, i)));
  };
  const grid = [0, 0.25, 0.5, 0.75, 1];
  return /*#__PURE__*/React.createElement("div", _extends({
    className: "aismat-trend " + className
  }, rest), extraOptions || note ? /*#__PURE__*/React.createElement("div", {
    className: "aismat-chartopts"
  }, extraOptions, note ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-chartnote"
  }, note) : null) : null, /*#__PURE__*/React.createElement("div", {
    className: "aismat-trend__readout"
  }, hov != null ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("b", null, labels[hov] != null ? labels[hov] : hov + 1)), series.map((s, i) => /*#__PURE__*/React.createElement("span", {
    key: i
  }, s.label, " ", /*#__PURE__*/React.createElement("b", {
    style: {
      color: s.color
    }
  }, s.data[hov] != null ? yFormat(s.data[hov]) : "—")))) : /*#__PURE__*/React.createElement("span", null, "hover for values")), /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 " + W + " " + H,
    onMouseMove: onMove,
    onMouseLeave: () => setHov(null)
  }, grid.map((g, i) => /*#__PURE__*/React.createElement("g", {
    key: i
  }, /*#__PURE__*/React.createElement("line", {
    x1: P.l,
    x2: W - P.r,
    y1: Y(lo + g * span),
    y2: Y(lo + g * span),
    stroke: "var(--grid-line)",
    strokeWidth: "1"
  }), /*#__PURE__*/React.createElement("text", {
    x: P.l - 5,
    y: Y(lo + g * span) + 3,
    fill: "var(--text-faint)",
    fontSize: "8.5",
    fontFamily: "'IBM Plex Mono', monospace",
    textAnchor: "end"
  }, yFormat(lo + g * span)))), labels.map((m, i) => /*#__PURE__*/React.createElement("text", {
    key: i,
    x: X(i),
    y: H - 6,
    fill: "var(--text-faint)",
    fontSize: "8.5",
    fontFamily: "'IBM Plex Mono', monospace",
    textAnchor: "middle"
  }, m)), hline ? /*#__PURE__*/React.createElement("g", null, /*#__PURE__*/React.createElement("line", {
    x1: P.l,
    x2: W - P.r,
    y1: Y(hline.value),
    y2: Y(hline.value),
    stroke: hline.color || "var(--baseline-line)",
    strokeWidth: "1",
    strokeDasharray: "5 4"
  }), hline.label ? /*#__PURE__*/React.createElement("text", {
    x: W - P.r,
    y: Y(hline.value) - 4,
    fill: hline.color || "var(--text-faint)",
    fontSize: "8.5",
    fontFamily: "'IBM Plex Mono', monospace",
    textAnchor: "end"
  }, hline.label) : null) : null, markers.map((m, i) => /*#__PURE__*/React.createElement("g", {
    key: i
  }, /*#__PURE__*/React.createElement("line", {
    x1: X(m.x),
    x2: X(m.x),
    y1: P.t,
    y2: H - P.b,
    stroke: m.color || "var(--accent-border)",
    strokeWidth: "1",
    strokeDasharray: "3 3"
  }), m.label ? /*#__PURE__*/React.createElement("text", {
    x: X(m.x) + 3,
    y: P.t + 8,
    fill: m.color || "var(--text-accent)",
    fontSize: "8.5",
    fontFamily: "'IBM Plex Mono', monospace"
  }, m.label) : null)), series.map((s, si) => {
    const pts = s.data.map((v, i) => [X(i), Y(v)]);
    const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    let len = 0;
    for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    len = Math.ceil(len) + 2;
    const anim = animate && !s.dashed;
    return /*#__PURE__*/React.createElement("path", {
      key: si,
      d: d,
      fill: "none",
      stroke: s.color,
      strokeWidth: s.width || 2.2,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      strokeDasharray: s.dashed ? "5 4" : anim ? len : undefined,
      className: anim ? "aismat-spark__line aismat-spark__line--animate" : "aismat-spark__line",
      style: anim ? {
        "--trend-length": len,
        animationDelay: si * 0.14 + "s"
      } : undefined
    });
  }), hov != null ? /*#__PURE__*/React.createElement("g", null, /*#__PURE__*/React.createElement("line", {
    x1: X(hov),
    x2: X(hov),
    y1: P.t,
    y2: H - P.b,
    stroke: "var(--text-faint)",
    strokeWidth: "1",
    strokeDasharray: "2 3"
  }), series.map((s, i) => s.data[hov] != null ? /*#__PURE__*/React.createElement("circle", {
    key: i,
    cx: X(hov),
    cy: Y(s.data[hov]),
    r: "3.2",
    fill: s.color,
    stroke: "var(--bg-panel)",
    strokeWidth: "1.4"
  }) : null)) : null));
}
Object.assign(__ds_scope, { TrendChart });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/instruments/TrendChart.jsx", error: String((e && e.message) || e) }); }

// components/navigation/AirGapIndicator.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const STATES = {
  airgapped: {
    tone: "pass",
    icon: "lock",
    text: "AIR-GAPPED"
  },
  local: {
    tone: "pass",
    icon: "hard-drive",
    text: "LOCAL ONLY"
  },
  online: {
    tone: "warn",
    icon: "wifi",
    text: "ONLINE"
  },
  breach: {
    tone: "fail",
    icon: "shield-alert",
    text: "EGRESS DETECTED"
  }
};

/**
 * AirGapIndicator — the persistent, undismissable data-sovereignty chip. Lives
 * in the status bar on every screen so Law 1 (nothing leaves the machine)
 * stays visible to the people responsible for it.
 */
function AirGapIndicator({
  state = "airgapped",
  label,
  blink = true,
  className = "",
  ...rest
}) {
  const c = STATES[state] || STATES.airgapped;
  return /*#__PURE__*/React.createElement("span", _extends({
    className: "aismat-airgap aismat-airgap--" + c.tone + " " + className,
    title: "Data sovereignty status"
  }, rest), /*#__PURE__*/React.createElement("span", {
    className: "aismat-airgap__dot",
    style: blink ? undefined : {
      animation: "none"
    }
  }), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: c.icon,
    size: 13
  }), label || c.text);
}
Object.assign(__ds_scope, { AirGapIndicator });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/AirGapIndicator.jsx", error: String((e && e.message) || e) }); }

// components/navigation/RoleStrip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * RoleStrip — the visible role switcher (never a hidden setting). Changes which
 * Act a viewer lands on and what the UI emphasizes — never the underlying data.
 */
function RoleStrip({
  roles = [],
  value,
  onChange,
  label = "Role",
  className = "",
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    className: "aismat-rolestrip " + className,
    role: "tablist",
    "aria-label": "Role"
  }, rest), label ? /*#__PURE__*/React.createElement("span", {
    className: "aismat-rolestrip__label"
  }, label) : null, roles.map(r => {
    const id = typeof r === "string" ? r : r.id;
    const rlabel = typeof r === "string" ? r : r.label;
    const active = id === value;
    return /*#__PURE__*/React.createElement("button", {
      key: id,
      type: "button",
      role: "tab",
      "aria-selected": active,
      className: "aismat-role" + (active ? " aismat-role--active" : ""),
      onClick: () => onChange && onChange(id)
    }, r.icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: r.icon,
      size: 15
    }) : null, rlabel);
  }));
}
Object.assign(__ds_scope, { RoleStrip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/RoleStrip.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Tabs — underline tab bar for the Act navigation and in-panel section
 * switches. Controlled: pass `value` and `onChange`.
 */
function Tabs({
  tabs = [],
  value,
  onChange,
  className = "",
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    className: "aismat-tabs " + className,
    role: "tablist"
  }, rest), tabs.map(t => {
    const id = typeof t === "string" ? t : t.id;
    const label = typeof t === "string" ? t : t.label;
    const active = id === value;
    return /*#__PURE__*/React.createElement("button", {
      key: id,
      type: "button",
      role: "tab",
      "aria-selected": active,
      className: "aismat-tab" + (active ? " aismat-tab--active" : ""),
      onClick: () => onChange && onChange(id)
    }, t.icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: t.icon,
      size: 15
    }) : null, label, t.badge != null ? /*#__PURE__*/React.createElement("span", {
      className: "aismat-tab__badge"
    }, t.badge) : null);
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActCompliance.jsx
try { (() => {
const {
  InstrumentPanel,
  MetricTile,
  AirGapIndicator,
  Checkbox,
  Button
} = window.AISMATCommandDeck_f4ddd5;
function ActCompliance({
  ctx
}) {
  const KIT = window.KIT;
  const [explain, setExplain] = React.useState(null);
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acthead"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Role station \xB7 Compliance / CUI Reviewer (GUARD)"), /*#__PURE__*/React.createElement("div", {
    className: "kit-acttitle"
  }, "Data sovereignty \u2014 audit view"), /*#__PURE__*/React.createElement("div", {
    className: "kit-actsub"
  }, "What left this machine, marked how, blocked when. The air-gap chip on every screen is load-bearing chrome; this station is its ledger.")), /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack"
  }, /*#__PURE__*/React.createElement(AirGapIndicator, {
    state: "airgapped"
  }), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "download",
    size: "sm"
  }, "Export audit log"))), /*#__PURE__*/React.createElement("div", {
    className: "kit-metricrow",
    style: {
      gridTemplateColumns: "repeat(3,1fr)"
    }
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Egress events \xB7 session",
    value: "0",
    valueTone: "pass",
    trendDir: "flat",
    trendTone: "pass",
    delta: "nothing leaves, by design",
    flag: "CONFIRMED"
  }), /*#__PURE__*/React.createElement(MetricTile, {
    label: "Outbound probes blocked",
    value: "2",
    valueTone: "warn",
    trendDir: "flat",
    trendTone: "neutral",
    delta: "telemetry, auto-denied",
    flag: "CONFIRMED"
  }), /*#__PURE__*/React.createElement(MetricTile, {
    label: "Exports \xB7 local only",
    value: "4",
    trendDir: "up",
    trendTone: "neutral",
    delta: "all CUI-marked",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-8"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "What left the machine",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Nothing has left this machine \u2014 ", /*#__PURE__*/React.createElement("b", null, "zero egress"), "; two outbound probes were blocked at the interface."),
    onExplain: () => setExplain({
      title: "Egress audit",
      what: "Every event that could move data, with its destination and whether anything crossed the boundary.",
      how: "The interface logs exports, ingests, and network attempts; the air-gap policy denies all egress and records the denial.",
      eg: "Before a classified review, export this log and staple it to the exhibit package — it is the proof that the analysis never touched a network."
    }),
    onDownload: () => {},
    onExpand: () => {}
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-tablewrap"
  }, /*#__PURE__*/React.createElement("table", {
    className: "kit-table"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Time"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Event"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Destination"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Egress"))), /*#__PURE__*/React.createElement("tbody", null, KIT.audit.map((a, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      cursor: "default"
    }
  }, /*#__PURE__*/React.createElement("td", {
    className: "kit-mono"
  }, a.time), /*#__PURE__*/React.createElement("td", {
    style: {
      color: "var(--text-primary)"
    }
  }, a.event), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono kit-muted"
  }, a.dest), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("span", {
    className: a.egress === "BLOCKED" ? "kit-audit-block" : "kit-audit-none"
  }, a.egress))))))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-4"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Marking & export policy",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Every export carries its ", /*#__PURE__*/React.createElement("b", null, "CUI banner"), "; the Console theme is stripped from print regardless of the live UI."),
    onExplain: () => setExplain({
      title: "Export policy",
      what: "The rules applied to every file that leaves the tool for local disk.",
      how: "One shared export service applies markings and theme rules, so no chart type can drift.",
      eg: "A screenshot of the Console theme in a courtroom is a credibility problem — the policy makes it impossible to export one by accident."
    })
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 12,
      paddingBottom: 4
    }
  }, /*#__PURE__*/React.createElement(Checkbox, {
    label: "CUI // SP-PROJ banner on every export",
    defaultChecked: true,
    disabled: true
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Strip Console theme from exports",
    defaultChecked: true,
    disabled: true
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Fact IDs embedded in AI narratives",
    defaultChecked: true,
    disabled: true
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Extras disabled in exhibit mode",
    defaultChecked: true
  }), /*#__PURE__*/React.createElement("div", {
    className: "kit-muted",
    style: {
      fontSize: 12,
      lineHeight: 1.5
    }
  }, "Locked rows are policy, not preference \u2014 Law 1 stays visible to the people responsible for it."))))), /*#__PURE__*/React.createElement(window.ExplainDialog, {
    open: !!explain,
    onClose: () => setExplain(null),
    ex: explain
  }));
}
window.ActCompliance = ActCompliance;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActCompliance.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActDataRoom.jsx
try { (() => {
const {
  InstrumentPanel,
  Dialog,
  Toast,
  Button,
  Icon,
  Checkbox,
  Select
} = window.AISMATCommandDeck_f4ddd5;
function ActDataRoom({
  ctx
}) {
  const [dlg, setDlg] = React.useState(null);
  const [toast, setToast] = React.useState(false);
  const rooms = [{
    ic: "file-spreadsheet",
    title: "Excel",
    desc: "Every table & chart — formulas intact where meaningful, not pasted values."
  }, {
    ic: "file-text",
    title: "Word",
    desc: "Formatted narrative report — findings, citations, and caveats inline."
  }, {
    ic: "file-down",
    title: "PDF",
    desc: "Print / archive-grade, CUI-marked. Never carries the Console theme, regardless of the live UI."
  }];
  const archive = [{
    name: "Falcon — forensic ledger",
    kind: "PDF",
    date: "2026-07-13",
    size: "2.4 MB"
  }, {
    name: "Portfolio health — all 14 programs",
    kind: "XLSX",
    date: "2026-07-13",
    size: "860 KB"
  }, {
    name: "SRA register — template",
    kind: "XLSX",
    date: "2026-07-06",
    size: "48 KB"
  }, {
    name: "Vega — DCMA-14 report",
    kind: "DOCX",
    date: "2026-07-01",
    size: "1.1 MB"
  }];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acthead"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Act V \xB7 Data Room"), /*#__PURE__*/React.createElement("div", {
    className: "kit-acttitle"
  }, "Nobody leaves empty-handed"), /*#__PURE__*/React.createElement("div", {
    className: "kit-actsub"
  }, "Everything you just walked through \u2014 exportable, templated, archivable. One shared export service keeps every format numerically identical to the on-screen value."))), /*#__PURE__*/React.createElement("div", {
    className: "kit-rooms"
  }, rooms.map(r => /*#__PURE__*/React.createElement("div", {
    className: "kit-room",
    key: r.title
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-room__ic"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: r.ic,
    size: 20
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-room__title"
  }, r.title, " export"), /*#__PURE__*/React.createElement("div", {
    className: "kit-room__desc"
  }, r.desc), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "download",
    size: "sm",
    onClick: () => setDlg(r.title)
  }, "Export ", r.title)))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Template round-trip",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "SRA register: download \u2192 fill offline \u2192 re-upload. A malformed template is ", /*#__PURE__*/React.createElement("b", null, "rejected with a specific, actionable error"), " \u2014 never silently half-loaded.")
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack",
    style: {
      gap: 10,
      padding: "4px 0 8px"
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "download",
    size: "sm"
  }, "Download template"), /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    iconLeft: "upload",
    size: "sm"
  }, "Upload filled register")))), /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow",
    style: {
      marginBottom: 10
    }
  }, "Archive \xB7 this machine only"), /*#__PURE__*/React.createElement("div", {
    className: "kit-archive"
  }, archive.map(a => /*#__PURE__*/React.createElement("div", {
    className: "kit-archive__row",
    key: a.name
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-archive__name"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "file",
    size: 15
  }), a.name), /*#__PURE__*/React.createElement("span", {
    className: "kit-mono kit-muted"
  }, a.kind), /*#__PURE__*/React.createElement("span", {
    className: "kit-mono kit-muted"
  }, a.date), /*#__PURE__*/React.createElement("span", {
    className: "kit-mono kit-muted"
  }, a.size)))), /*#__PURE__*/React.createElement(Dialog, {
    open: !!dlg,
    onClose: () => setDlg(null),
    title: "Export " + (dlg || ""),
    subtitle: "CUI-marked \xB7 values identical to on-screen",
    footer: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      onClick: () => setDlg(null)
    }, "Cancel"), /*#__PURE__*/React.createElement(Button, {
      iconLeft: "download",
      onClick: () => {
        setDlg(null);
        setToast(true);
      }
    }, "Export"))
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(Checkbox, {
    label: "Include forensic fact ledger",
    defaultChecked: true
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Include DCMA-14 detail",
    defaultChecked: true
  }), /*#__PURE__*/React.createElement(Checkbox, {
    label: "Include AI narrative (with citations)"
  }), /*#__PURE__*/React.createElement(Select, {
    label: "Scope",
    options: ["Program Falcon", "All 14 programs", "Selected activities"]
  }))), toast ? /*#__PURE__*/React.createElement("div", {
    style: {
      position: "fixed",
      right: 24,
      bottom: 52,
      zIndex: 200
    }
  }, /*#__PURE__*/React.createElement(Toast, {
    status: "pass",
    title: "Export complete",
    onClose: () => setToast(false)
  }, "CUI-marked file saved \u2014 values identical to on-screen.")) : null);
}
window.ActDataRoom = ActDataRoom;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActDataRoom.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActDeepDive.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  InstrumentPanel,
  MetricTile,
  DcmaStrip,
  StatusChip,
  Tooltip,
  CitationChip,
  CaveatBanner,
  Button,
  Tabs,
  GanttChart,
  TrendChart
} = window.AISMATCommandDeck_f4ddd5;
function evmPoints(series, maxV, w, h, pad) {
  const n = series.length;
  return series.map((v, i) => {
    const x = pad + i / (n - 1) * (w - pad * 2);
    const y = h - pad - v / maxV * (h - pad * 2);
    return x.toFixed(1) + "," + y.toFixed(1);
  }).join(" ");
}
const DD_EXPLAIN = {
  gantt: {
    title: "Driving path & schedule",
    what: "Every activity as a bar on a shared timeline; gold bars are on the driving/critical path, dashed tails are free float, the dashed vertical line is the data date.",
    how: "CPM forward/backward pass over the current update's network — dates and float come from the engine, not the chart.",
    eg: "If a gold bar slips, the finish slips day-for-day. If a grey bar's dashed tail disappears across updates, it is about to join the critical path — act before it does."
  },
  dcma: {
    title: "DCMA-14 scorecard",
    what: "The 14 industry schedule-quality checks, pass/fail, numbered in standard order.",
    how: "Each check is computed per the DCMA 14-point assessment (via the NASA Acumen .aft library) against the current update.",
    eg: "Below 12/14, treat the schedule's dates as suspect: a network full of hard constraints or negative float produces confident-looking dates that won't survive scrutiny."
  },
  evm: {
    title: "EVM curves",
    what: "Planned value, earned value, and actual cost, cumulative over time.",
    how: "PV/EV/AC per ANSI/EIA-748 from the cost-loaded schedule; SPI = EV÷PV, CPI = EV÷AC.",
    eg: "EV below PV but above AC = behind schedule, under cost: the program is trading schedule for burn rate. Watch TCPI — above ~1.05 the recovery math stops being credible."
  },
  hist: {
    title: "Total-float histogram",
    what: "How many activities sit in each float band, from negative to comfortable.",
    how: "Total float per activity from the CPM run, bucketed.",
    eg: "A healthy network is bell-ish around mid float. Mass piling into <0d and 0–5d means the schedule is going brittle — small hits will cascade."
  },
  trends: {
    title: "Metric trends",
    what: "Each health measure across the last seven schedule updates.",
    how: "One point per submitted update; nothing interpolated.",
    eg: "Direction beats level: SPI 0.92 and rising is a recovery story, SPI 0.96 and falling for five updates is a claim brewing."
  },
  compare: {
    title: "Compare updates",
    what: "This update's Gantt against the previous baseline — morph between them.",
    how: "Both networks' dates from the engine; bars animate between geometries and changed activities flash.",
    eg: "Watch WHAT moved, not just how much: if only successors of one slipped activity moved, that's a clean delay chain — the fragnet for your time-impact analysis."
  }
};
function ActDeepDive({
  ctx
}) {
  const KIT = window.KIT;
  const prog = KIT.programs.find(p => p.id === ctx.program) || KIT.programs[0];
  const [tab, setTab] = React.useState(ctx.role === "evm" ? "evm" : ctx.role === "legal" ? "forensics" : "instruments");
  const [depth, setDepth] = React.useState(null);
  const [explain, setExplain] = React.useState(null);
  const [phase, setPhase] = React.useState("current");
  const evm = KIT.evm;
  const maxV = Math.max(...evm.pv) * 1.08;
  const W = 340,
    H = 150,
    P = 16;
  const fails = KIT.dcma.filter(d => d.status !== "pass");
  const maxCount = Math.max(...KIT.floatHist.map(f => f.count));
  const tr = KIT.trends;
  const fmt2 = v => v.toFixed(2);
  const ganttDepth = () => setDepth({
    title: "Driving path — full data",
    sub: "Update #42 · " + prog.name,
    columns: [{
      key: "id",
      label: "ID",
      mono: true
    }, {
      key: "name",
      label: "Activity"
    }, {
      key: "s",
      label: "Start wk",
      mono: true
    }, {
      key: "d",
      label: "Dur",
      mono: true
    }, {
      key: "tf",
      label: "TF",
      mono: true
    }, {
      key: "crit",
      label: "Driving"
    }],
    rows: KIT.activities.map(a => ({
      ...a,
      crit: a.crit ? "Yes" : "—"
    }))
  });
  const trendDepth = () => setDepth({
    title: "Metric trends — full data",
    sub: "Updates #36–#42 · " + prog.name,
    columns: [{
      key: "u",
      label: "Update",
      mono: true
    }, {
      key: "spi",
      label: "SPI",
      mono: true
    }, {
      key: "cpi",
      label: "CPI",
      mono: true
    }, {
      key: "tcpi",
      label: "TCPI",
      mono: true
    }, {
      key: "float",
      label: "Float (d)",
      mono: true
    }, {
      key: "dcma",
      label: "DCMA",
      mono: true
    }, {
      key: "eac",
      label: "EAC ($M)",
      mono: true
    }],
    rows: KIT.updates.map((u, i) => ({
      u,
      spi: tr.spi[i],
      cpi: tr.cpi[i],
      tcpi: tr.tcpi[i],
      float: tr.floatTotal[i],
      dcma: tr.dcmaPass[i] + "/14",
      eac: tr.eac[i]
    }))
  });
  const evmDepth = () => setDepth({
    title: "EVM curves — full data",
    sub: "Cumulative $M · " + prog.name,
    columns: [{
      key: "m",
      label: "Month"
    }, {
      key: "pv",
      label: "PV",
      mono: true
    }, {
      key: "ev",
      label: "EV",
      mono: true
    }, {
      key: "ac",
      label: "AC",
      mono: true
    }],
    rows: evm.months.map((m, i) => ({
      m,
      pv: evm.pv[i],
      ev: evm.ev[i],
      ac: evm.ac[i]
    }))
  });
  const noop = () => {};
  const lowFloat = ctx.extras ? "This one's driving your whole schedule — buy it a coffee." : null;
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acthead"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Act III \xB7 Program Deep-Dive"), /*#__PURE__*/React.createElement("div", {
    className: "kit-acttitle"
  }, "Program ", prog.name), /*#__PURE__*/React.createElement("div", {
    className: "kit-actsub"
  }, "Every visual is an instrument: a plain-English takeaway, a legend, and the same toolbar \u2014 how-to-read, grid, export, expand. Scheduler view at full depth.")), /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack"
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    iconLeft: "arrow-left",
    size: "sm",
    onClick: () => ctx.setAct("portfolio")
  }, "Portfolio"), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "git-compare",
    size: "sm",
    onClick: () => setTab("compare")
  }, "Compare updates"))), /*#__PURE__*/React.createElement("div", {
    className: "kit-metricrow"
  }, /*#__PURE__*/React.createElement(Tooltip, {
    className: "kit-ttblock",
    what: "Schedule Performance Index \u2014 0.92.",
    how: "EV \xF7 PV per ANSI/EIA-748, from update #42.",
    example: "Below 1.00 the program earns slower than planned; each 0.01 \u2248 one lost day per hundred planned."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Schedule Perf. Index",
    value: prog.spi.toFixed(2),
    valueTone: prog.spi < 1 ? "fail" : "pass",
    trendDir: "down",
    trendTone: "fail",
    delta: "-0.06 vs #41",
    flag: "SUSPECTED"
  })), /*#__PURE__*/React.createElement(Tooltip, {
    className: "kit-ttblock",
    what: "Cost Performance Index \u2014 1.04.",
    how: "EV \xF7 AC per ANSI/EIA-748.",
    example: "Above 1.00, each dollar spent earns more than a dollar of planned work \u2014 cost is not the problem here."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Cost Perf. Index",
    value: prog.cpi.toFixed(2),
    valueTone: prog.cpi >= 1 ? "pass" : "fail",
    trendDir: "up",
    trendTone: "pass",
    delta: "+0.02 vs #41",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(Tooltip, {
    className: "kit-ttblock",
    what: "To-Complete Performance Index \u2014 1.08.",
    how: "(BAC \u2212 EV) \xF7 (BAC \u2212 AC): the efficiency needed from here on to hit budget.",
    example: "TCPI above CPI means the plan assumes you'll suddenly work better than you ever have. Above ~1.05, escalate."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "TCPI (to BAC)",
    value: "1.08",
    trendDir: "up",
    trendTone: "warn",
    delta: "above CPI \u2014 at risk",
    flag: "SUSPECTED"
  })), /*#__PURE__*/React.createElement(Tooltip, {
    className: "kit-ttblock",
    what: "DCMA-14 pass count \u2014 11 of 14.",
    how: "The 14 schedule-quality checks, per the DCMA assessment.",
    example: "11/14 is workable; the two open breaches (hard constraints, negative float) are exactly what opposing experts attack first."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "DCMA-14 pass",
    value: prog.dcmaPass,
    unit: "/14",
    trendDir: "up",
    trendTone: "pass",
    delta: "+2 checks",
    flag: "CONFIRMED"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement(Tabs, {
    value: tab,
    onChange: setTab,
    tabs: [{
      id: "instruments",
      label: "Instruments",
      icon: "gauge"
    }, {
      id: "trends",
      label: "Trends",
      icon: "trending-up",
      badge: "7 updates"
    }, {
      id: "evm",
      label: "EVM",
      icon: "bar-chart-3",
      badge: "8 metrics"
    }, {
      id: "quality",
      label: "Quality",
      icon: "badge-check",
      badge: "71/100"
    }, {
      id: "forensics",
      label: "Forensics",
      icon: "fingerprint",
      badge: "62"
    }, {
      id: "compare",
      label: "Compare updates",
      icon: "git-compare",
      badge: "#41→#42"
    }]
  })), tab === "instruments" ? /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-8"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Driving path & schedule",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "The ", /*#__PURE__*/React.createElement("b", null, "Building envelope"), " slip pushed Commissioning onto the critical path \u2014 gold bars are driving, dashed segments are free float."),
    legend: [{
      label: "Driving / critical",
      color: "var(--status-driving)"
    }, {
      label: "Non-critical",
      color: "var(--deck-500)"
    }, {
      label: "Free float",
      color: "var(--border-strong)"
    }],
    onExplain: () => setExplain(DD_EXPLAIN.gantt),
    onGrid: ganttDepth,
    onDownload: noop,
    onExpand: ganttDepth
  }, /*#__PURE__*/React.createElement(GanttChart, {
    activities: KIT.activities,
    dataDate: 13,
    note: "wk from start \xB7 DD = data date",
    lowFloatBadge: lowFloat
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-4"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "DCMA-14 scorecard",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "11 of 14 checks pass. ", /*#__PURE__*/React.createElement("b", null, "Hard constraints"), " and ", /*#__PURE__*/React.createElement("b", null, "negative float"), " are the two open breaches."),
    onExplain: () => setExplain(DD_EXPLAIN.dcma),
    onExpand: () => setDepth({
      title: "DCMA-14 — all checks",
      sub: "Update #42",
      columns: [{
        key: "n",
        label: "#",
        mono: true
      }, {
        key: "name",
        label: "Check"
      }, {
        key: "status",
        label: "Result"
      }],
      rows: KIT.dcma
    })
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 14
    }
  }, /*#__PURE__*/React.createElement(DcmaStrip, {
    results: KIT.dcma
  }), /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 8
    }
  }, fails.map(f => /*#__PURE__*/React.createElement("div", {
    key: f.n,
    className: "kit-hstack",
    style: {
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: "var(--text-secondary)"
    }
  }, f.n, ". ", f.name), /*#__PURE__*/React.createElement(StatusChip, {
    status: f.status
  }, f.status === "fail" ? "Breach" : "Watch"))), /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack",
    style: {
      gap: 6,
      marginTop: 2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: "var(--text-muted)"
    }
  }, "Full check 5 detail"), /*#__PURE__*/React.createElement(CitationChip, {
    id: "FACT-4420",
    onClick: () => ctx.setAct("ledger")
  })))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-7"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "EVM curves",
    flag: "SUSPECTED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Earned value is tracking ", /*#__PURE__*/React.createElement("b", null, "below plan"), " and above cost \u2014 schedule is being traded for burn rate."),
    legend: [{
      label: "PV (planned)",
      color: "var(--viz-3)"
    }, {
      label: "EV (earned)",
      color: "var(--viz-1)"
    }, {
      label: "AC (actual)",
      color: "var(--viz-2)"
    }],
    onExplain: () => setExplain(DD_EXPLAIN.evm),
    onGrid: evmDepth,
    onDownload: noop,
    onExpand: evmDepth
  }, /*#__PURE__*/React.createElement("svg", {
    className: "kit-chart",
    viewBox: "0 0 " + W + " " + H,
    style: {
      height: 168
    }
  }, [0, 0.25, 0.5, 0.75, 1].map((g, i) => /*#__PURE__*/React.createElement("line", {
    key: i,
    x1: P,
    x2: W - P,
    y1: H - P - g * (H - P * 2),
    y2: H - P - g * (H - P * 2),
    stroke: "var(--grid-line)",
    strokeWidth: "1",
    vectorEffect: "non-scaling-stroke"
  })), /*#__PURE__*/React.createElement("polyline", {
    points: evmPoints(evm.pv, maxV, W, H, P),
    fill: "none",
    stroke: "var(--viz-3)",
    strokeWidth: "2",
    strokeDasharray: "4 3",
    vectorEffect: "non-scaling-stroke"
  }), /*#__PURE__*/React.createElement("polyline", {
    points: evmPoints(evm.ac, maxV, W, H, P),
    fill: "none",
    stroke: "var(--viz-2)",
    strokeWidth: "2",
    vectorEffect: "non-scaling-stroke"
  }), /*#__PURE__*/React.createElement("polyline", {
    points: evmPoints(evm.ev, maxV, W, H, P),
    fill: "none",
    stroke: "var(--viz-1)",
    strokeWidth: "2.5",
    vectorEffect: "non-scaling-stroke"
  }), evm.months.map((m, i) => /*#__PURE__*/React.createElement("text", {
    key: i,
    x: P + i / (evm.months.length - 1) * (W - P * 2),
    y: H - 3,
    fill: "var(--text-faint)",
    fontSize: "9",
    fontFamily: "'IBM Plex Mono', monospace",
    textAnchor: "middle"
  }, m))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-5"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Total-float histogram",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Six activities sit at ", /*#__PURE__*/React.createElement("b", null, "negative float"), " \u2014 they are already late against the network."),
    onExplain: () => setExplain(DD_EXPLAIN.hist),
    onExpand: () => setDepth({
      title: "Float distribution — bands",
      sub: "Update #42",
      columns: [{
        key: "band",
        label: "Band",
        mono: true
      }, {
        key: "count",
        label: "Activities",
        mono: true
      }],
      rows: KIT.floatHist
    })
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-hist"
  }, KIT.floatHist.map((f, i) => /*#__PURE__*/React.createElement("div", {
    className: "kit-hist__col",
    key: i
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-hist__n"
  }, f.count), /*#__PURE__*/React.createElement("div", {
    className: "kit-hist__bar",
    style: {
      height: f.count / maxCount * 100 + "%",
      background: "var(--status-" + f.tone + ")"
    }
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-hist__lab"
  }, f.band)))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Driving-path explorer",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Five activities carry the finish date \u2014 the ", /*#__PURE__*/React.createElement("b", null, "FS+2d lag"), " into Commissioning is unexplained buffer; name the work or remove it."),
    legend: [{
      label: "Driving activity",
      color: "var(--status-driving)"
    }],
    onExplain: () => setExplain({
      title: "Driving-path explorer",
      what: "The exact logic chain controlling the project finish: each driving activity, the relationship type and lag that hands off to the next, and its float.",
      how: "Longest-path trace from data date to finish over the CPM network; relationship labels come straight from the native file.",
      eg: "Read the LINKS, not just the bars: an FS+2d lag on the driving path is two invisible days nobody is managing — either it's real work (name it) or it's padding (cut it)."
    }),
    onGrid: () => setDepth({
      title: "Driving-path logic — relationships",
      sub: "Update #42 · pred → succ",
      columns: [{
        key: "pred",
        label: "Predecessor",
        mono: true
      }, {
        key: "succ",
        label: "Successor",
        mono: true
      }, {
        key: "type",
        label: "Type",
        mono: true
      }, {
        key: "lag",
        label: "Lag (d)",
        mono: true
      }, {
        key: "driving",
        label: "Driving"
      }],
      rows: KIT.rels
    }),
    onDownload: noop,
    onExpand: () => setDepth({
      title: "Driving-path logic — relationships",
      sub: "Update #42 · pred → succ",
      columns: [{
        key: "pred",
        label: "Predecessor",
        mono: true
      }, {
        key: "succ",
        label: "Successor",
        mono: true
      }, {
        key: "type",
        label: "Type",
        mono: true
      }, {
        key: "lag",
        label: "Lag (d)",
        mono: true
      }, {
        key: "driving",
        label: "Driving"
      }],
      rows: KIT.rels
    })
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-chain"
  }, KIT.activities.filter(a => a.crit).map((a, i, arr) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: a.id
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-chain__node"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-chain__id"
  }, a.id), /*#__PURE__*/React.createElement("div", {
    className: "kit-chain__nm"
  }, a.name), /*#__PURE__*/React.createElement("div", {
    className: "kit-chain__tf"
  }, "TF ", a.tf, "d \xB7 wk ", a.s, "\u2013", a.s + a.d)), i < arr.length - 1 ? /*#__PURE__*/React.createElement("div", {
    className: "kit-chain__link"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-chain__rel"
  }, KIT.drivingLinks[i].type, KIT.drivingLinks[i].lag ? "+" + KIT.drivingLinks[i].lag + "d" : ""), /*#__PURE__*/React.createElement("span", {
    className: "kit-chain__arrow"
  }, "\u2192")) : null)))))) : null, tab === "trends" ? /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(CaveatBanner, {
    status: "warn",
    title: "SUSPECTED \u2014 EVM CAVEATS APPLY"
  }, "SPI uses an earning-rule that may not match this schedule's %-complete method, and the TCPI pass/fail direction is under review in the engine backlog. Flags stay visible on every chart below \u2014 never hidden behind a clean number.")), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-6"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Total float \xB7 trend",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Falcon has bled float for ", /*#__PURE__*/React.createElement("b", null, "six consecutive updates"), " \u2014 and the loss is accelerating."),
    legend: [{
      label: "Driving-path total float (d)",
      color: "var(--status-fail)"
    }],
    onExplain: () => setExplain(DD_EXPLAIN.trends),
    onGrid: trendDepth,
    onDownload: noop,
    onExpand: trendDepth
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.updates,
    series: [{
      label: "Float",
      color: "var(--status-fail)",
      data: tr.floatTotal
    }],
    yFormat: v => Math.round(v) + "d",
    hline: {
      value: 0,
      label: "critical",
      color: "var(--status-warn)"
    },
    markers: [{
      x: 3,
      label: "envelope slip"
    }],
    height: 165
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-6"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "SPI / CPI / TCPI \xB7 trend",
    flag: "SUSPECTED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "SPI falls while CPI holds \u2014 ", /*#__PURE__*/React.createElement("b", null, "schedule traded for burn rate"), "; TCPI above 1.05 says the recovery math is strained."),
    legend: [{
      label: "SPI",
      color: "var(--viz-1)"
    }, {
      label: "CPI",
      color: "var(--viz-2)"
    }, {
      label: "TCPI",
      color: "var(--viz-4)"
    }],
    onExplain: () => setExplain(DD_EXPLAIN.trends),
    onGrid: trendDepth,
    onDownload: noop,
    onExpand: trendDepth
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.updates,
    series: [{
      label: "SPI",
      color: "var(--viz-1)",
      data: tr.spi
    }, {
      label: "CPI",
      color: "var(--viz-2)",
      data: tr.cpi
    }, {
      label: "TCPI",
      color: "var(--viz-4)",
      data: tr.tcpi
    }],
    yFormat: fmt2,
    hline: {
      value: 1.0,
      label: "on plan"
    },
    height: 165
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-6"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "DCMA-14 pass rate \xB7 trend",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Quality recovered to ", /*#__PURE__*/React.createElement("b", null, "11/14"), " after the constraint cleanup in #41 \u2014 keep removing hard constraints."),
    legend: [{
      label: "Checks passing (of 14)",
      color: "var(--status-pass)"
    }],
    onExplain: () => setExplain(DD_EXPLAIN.trends),
    onGrid: trendDepth,
    onDownload: noop,
    onExpand: trendDepth
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.updates,
    series: [{
      label: "Pass",
      color: "var(--status-pass)",
      data: tr.dcmaPass
    }],
    yMin: 7,
    yMax: 14,
    yFormat: v => Math.round(v) + "",
    markers: [{
      x: 5,
      label: "cleanup"
    }],
    height: 165
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-6"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "EAC vs budget \xB7 trend",
    flag: "SUSPECTED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Estimate at completion has drifted ", /*#__PURE__*/React.createElement("b", null, "$5M above BAC"), " \u2014 variance at completion is now negative."),
    legend: [{
      label: "EAC ($M)",
      color: "var(--viz-2)"
    }, {
      label: "Earned schedule (wk)",
      color: "var(--viz-1)"
    }],
    onExplain: () => setExplain(DD_EXPLAIN.trends),
    onGrid: trendDepth,
    onDownload: noop,
    onExpand: trendDepth
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.updates,
    series: [{
      label: "EAC",
      color: "var(--viz-2)",
      data: tr.eac
    }, {
      label: "ES",
      color: "var(--viz-1)",
      data: tr.es,
      dashed: true
    }],
    hline: {
      value: tr.bac,
      label: "BAC 150"
    },
    yFormat: v => Math.round(v) + "",
    height: 165
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-6"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Milestone slip \xB7 trend",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("b", null, "Turnover"), " has slipped 14 days against baseline \u2014 slip is compounding through the driving path."),
    legend: [{
      label: "Design freeze",
      color: "var(--viz-1)"
    }, {
      label: "IOT&E start",
      color: "var(--viz-3)"
    }, {
      label: "Turnover",
      color: "var(--status-fail)"
    }],
    onExplain: () => setExplain({
      title: "Milestone slip",
      what: "Each contractual milestone's forecast date, expressed as days late against baseline, per update.",
      how: "Forecast date minus baseline date, from each update's CPM run.",
      eg: "Parallel slip lines mean one upstream driver is dragging everything — fix the driver, not each milestone."
    }),
    onGrid: () => setDepth({
      title: "Milestone slip — data",
      sub: "Days late vs baseline",
      columns: [{
        key: "u",
        label: "Update",
        mono: true
      }, {
        key: "m0",
        label: KIT.milestones.names[0],
        mono: true
      }, {
        key: "m1",
        label: KIT.milestones.names[1],
        mono: true
      }, {
        key: "m2",
        label: KIT.milestones.names[2],
        mono: true
      }],
      rows: KIT.updates.map((u, i) => ({
        u,
        m0: "+" + KIT.milestones.slip[0][i] + "d",
        m1: "+" + KIT.milestones.slip[1][i] + "d",
        m2: "+" + KIT.milestones.slip[2][i] + "d"
      }))
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.updates,
    series: [{
      label: "Design freeze",
      color: "var(--viz-1)",
      data: KIT.milestones.slip[0]
    }, {
      label: "IOT&E",
      color: "var(--viz-3)",
      data: KIT.milestones.slip[1]
    }, {
      label: "Turnover",
      color: "var(--status-fail)",
      data: KIT.milestones.slip[2]
    }],
    yFormat: v => "+" + Math.round(v) + "d",
    hline: {
      value: 0,
      label: "baseline"
    },
    height: 165
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-6"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Schedule density \xB7 trend",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Work-in-progress peaked at ", /*#__PURE__*/React.createElement("b", null, "38 concurrent activities"), " in May \u2014 density is falling as fronts close."),
    legend: [{
      label: "Activities in progress",
      color: "var(--viz-4)"
    }],
    onExplain: () => setExplain({
      title: "Schedule density",
      what: "How many activities are in progress in each period.",
      how: "Count of activities whose dates span the period, per update.",
      eg: "A late-program density spike means stacking trades — the classic prelude to out-of-sequence progress and quality claims."
    }),
    onGrid: () => setDepth({
      title: "Schedule density — data",
      sub: "Active per month",
      columns: [{
        key: "m",
        label: "Month"
      }, {
        key: "n",
        label: "Active",
        mono: true
      }],
      rows: KIT.evm.months.map((m, i) => ({
        m,
        n: KIT.quality.density[i]
      }))
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.evm.months,
    series: [{
      label: "Active",
      color: "var(--viz-4)",
      data: KIT.quality.density
    }],
    yFormat: v => Math.round(v) + "",
    height: 165
  })))) : null, tab === "compare" ? /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Before / after \u2014 update #41 \u2192 #42",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Morph the two updates instead of spot-the-difference: ", /*#__PURE__*/React.createElement("b", null, "Building envelope"), " slid a week and dragged Commissioning and Turnover with it."),
    legend: [{
      label: "Driving / critical",
      color: "var(--status-driving)"
    }, {
      label: "Non-critical",
      color: "var(--deck-500)"
    }, {
      label: "Baseline #41 (ghost)",
      color: "var(--border-strong)"
    }],
    onExplain: () => setExplain(DD_EXPLAIN.compare),
    onGrid: ganttDepth,
    onDownload: noop,
    onExpand: ganttDepth
  }, /*#__PURE__*/React.createElement(GanttChart, {
    activities: KIT.activities,
    phase: phase,
    defaultBaseline: true,
    dataDate: 13,
    note: "showing " + (phase === "current" ? "update #42" : "baseline #41"),
    lowFloatBadge: lowFloat,
    extraOptions: /*#__PURE__*/React.createElement("button", {
      type: "button",
      className: "aismat-chartopt" + (phase === "baseline" ? " aismat-chartopt--on" : ""),
      onClick: () => setPhase(phase === "current" ? "baseline" : "current"),
      "aria-pressed": phase === "baseline"
    }, "\u21C4 Morph #41/#42")
  })))) : null, tab === "evm" ? /*#__PURE__*/React.createElement(window.DeepDiveEVM, {
    ctx: ctx,
    setDepth: setDepth,
    setExplain: setExplain
  }) : null, tab === "quality" ? /*#__PURE__*/React.createElement(window.DeepDiveQuality, {
    ctx: ctx,
    setDepth: setDepth,
    setExplain: setExplain
  }) : null, tab === "forensics" ? /*#__PURE__*/React.createElement(window.DeepDiveForensics, {
    ctx: ctx,
    setDepth: setDepth,
    setExplain: setExplain
  }) : null, /*#__PURE__*/React.createElement(window.DepthDialog, _extends({
    open: !!depth,
    onClose: () => setDepth(null)
  }, depth || {})), /*#__PURE__*/React.createElement(window.ExplainDialog, {
    open: !!explain,
    onClose: () => setExplain(null),
    ex: explain
  }));
}
window.ActDeepDive = ActDeepDive;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActDeepDive.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActIngest.jsx
try { (() => {
/* Data station — Ingest & updates: multiple native file types, one doctrine:
   no silent failures. */
const {
  InstrumentPanel,
  StatusChip,
  Badge,
  Button,
  Icon,
  CaveatBanner
} = window.AISMATCommandDeck_f4ddd5;
function ActIngest({
  ctx
}) {
  const KIT = window.KIT;
  const ig = KIT.ingest;
  const [explain, setExplain] = React.useState(null);
  const noop = () => {};
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acthead"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Data \xB7 Ingest & updates"), /*#__PURE__*/React.createElement("div", {
    className: "kit-acttitle"
  }, "Native file types, no silent failures"), /*#__PURE__*/React.createElement("div", {
    className: "kit-actsub"
  }, "AISMAT reads the schedule in its native format \u2014 P6 XER, MPP, XML, XLSX, CSV, JSON \u2014 and either loads it whole or rejects it with a specific, actionable reason. Never half-loaded.")), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "upload",
    size: "sm"
  }, "Import schedule")), /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-5"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Import",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Drop any supported export \u2014 parsing happens ", /*#__PURE__*/React.createElement("b", null, "on this machine"), "; nothing is uploaded anywhere."),
    onExplain: () => setExplain({
      title: "Import",
      what: "The entry point for schedule data: native P6/MSP formats plus tabular exports and the AISMAT interchange JSON.",
      how: "Files are parsed locally; the air-gap policy applies to ingest exactly as it does to export.",
      eg: "Monthly ritual: drop the contractor's XER the day it arrives — the diff against last update (logic edits, constraint changes) is your first read, before anyone briefs you."
    })
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-drop"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "file-input",
    size: 22
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-drop__title"
  }, "Drop a schedule to ingest"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12
    }
  }, "XER \xB7 MPP \xB7 XML \xB7 XLSX \xB7 CSV \xB7 JSON")), /*#__PURE__*/React.createElement("div", {
    className: "kit-fmts"
  }, ig.formats.map(f => /*#__PURE__*/React.createElement("div", {
    className: "kit-fmt",
    key: f.ext
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-fmt__ext"
  }, f.ext), /*#__PURE__*/React.createElement("span", {
    className: "kit-fmt__app"
  }, f.app)))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-7"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Last ingest \u2014 pipeline",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("b", null, "falcon_2026-07-13.xer"), " loaded as Update #42 \u2014 two rows quarantined with reasons, everything else whole."),
    onExplain: () => setExplain({
      title: "Ingest pipeline",
      what: "The four stages every file passes: parse → validate → CPM run → fact ledger.",
      how: "Each stage either completes for the whole file or stops with the exact failing rows; the fact ledger is written last so no partial state ever renders.",
      eg: "If Validate shows quarantined rows, fix those rows in the source tool and re-import — don't hand-edit inside AISMAT; the ledger must trace to the native file."
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-pipe"
  }, ig.pipeline.map((p, i) => /*#__PURE__*/React.createElement("div", {
    className: "kit-pipe__row",
    key: p.step
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-pipe__n"
  }, i + 1), /*#__PURE__*/React.createElement("span", {
    className: "kit-pipe__step"
  }, p.step), /*#__PURE__*/React.createElement("span", {
    className: "kit-pipe__desc"
  }, p.desc), /*#__PURE__*/React.createElement(StatusChip, {
    status: p.status
  }, p.status === "pass" ? "Complete" : "2 quarantined")))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Rejected rows \u2014 with reasons",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "A malformed row is rejected with a ", /*#__PURE__*/React.createElement("b", null, "specific, actionable error"), " \u2014 the import doctrine, applied to every format."),
    onExplain: () => setExplain({
      title: "Rejections",
      what: "Every quarantined row from the last ingest and exactly why it failed.",
      how: "Validation rules per format (circular logic, undefined calendars, missing durations); the reason names the fix.",
      eg: "\"Row 14 has a blank most-likely duration\" beats \"import error\" — the scheduler fixes it in one pass instead of a support ticket."
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 0
    }
  }, ig.rejections.map(r => /*#__PURE__*/React.createElement("div", {
    key: r.row,
    className: "kit-pattern"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-pattern__name"
  }, r.row), /*#__PURE__*/React.createElement("div", {
    className: "kit-pattern__detail"
  }, r.reason)), /*#__PURE__*/React.createElement(StatusChip, {
    status: "fail"
  }, "Quarantined")))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Update history",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Seven updates on file \u2014 any two can be ", /*#__PURE__*/React.createElement("b", null, "morphed in Compare"), "; every fact cites the update it came from."),
    onExplain: () => setExplain({
      title: "Update history",
      what: "Every schedule version ingested, with source file, format, and the health delta it introduced.",
      how: "Updates are immutable once loaded; comparisons and windows analysis always reference them by id.",
      eg: "In a claim, the update history IS the chain of custody — export it alongside the ledger so the other side can reproduce your numbers."
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-tablewrap"
  }, /*#__PURE__*/React.createElement("table", {
    className: "kit-table"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Update"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Source file"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Format"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Activities"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Health \u0394"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Loaded"))), /*#__PURE__*/React.createElement("tbody", null, ig.history.map(h => /*#__PURE__*/React.createElement("tr", {
    key: h.upd,
    style: {
      cursor: "default"
    }
  }, /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement(Badge, {
    tone: "accent"
  }, h.upd)), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono",
    style: {
      color: "var(--text-primary)"
    }
  }, h.file), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono kit-muted"
  }, h.fmt), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono"
  }, h.acts), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono",
    style: {
      color: "var(--status-fail)"
    }
  }, h.delta), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono kit-muted"
  }, h.when))))))))), /*#__PURE__*/React.createElement(window.ExplainDialog, {
    open: !!explain,
    onClose: () => setExplain(null),
    ex: explain
  }));
}
window.ActIngest = ActIngest;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActIngest.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActLedger.jsx
try { (() => {
const {
  InstrumentPanel,
  CaveatBanner,
  CitationChip,
  StatusChip,
  Button
} = window.AISMATCommandDeck_f4ddd5;
function ActLedger({
  ctx
}) {
  const KIT = window.KIT;
  const [sel, setSel] = React.useState(KIT.facts[0].id);
  const fact = KIT.facts.find(f => f.id === sel) || KIT.facts[0];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acthead"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Act IV \xB7 Forensic Ledger"), /*#__PURE__*/React.createElement("div", {
    className: "kit-acttitle"
  }, "Defend the number"), /*#__PURE__*/React.createElement("div", {
    className: "kit-actsub"
  }, "Citations first, narrative second, raw data one click behind every claim. This role never sees an AI sentence without its supporting fact IDs.")), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "download",
    size: "sm"
  }, "Export ledger")), /*#__PURE__*/React.createElement("div", {
    className: "kit-ledger"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-ledger__list"
  }, KIT.facts.map(f => /*#__PURE__*/React.createElement("button", {
    key: f.id,
    className: "kit-lgitem" + (f.id === sel ? " kit-lgitem--active" : ""),
    onClick: () => setSel(f.id)
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-lgitem__label"
  }, f.label), /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack",
    style: {
      justifyContent: "space-between",
      marginTop: 4
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-lgitem__val"
  }, f.value), f.confirmed ? /*#__PURE__*/React.createElement(StatusChip, {
    status: "pass"
  }, "Confirmed") : /*#__PURE__*/React.createElement(StatusChip, {
    status: "fail"
  }, "Suspected"))))), /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: fact.id,
    flag: fact.confirmed ? "CONFIRMED" : "SUSPECTED",
    takeaway: fact.label,
    onDownload: () => {},
    onExpand: () => {}
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-fact__value",
    style: {
      margin: "4px 0 14px"
    }
  }, fact.value), !fact.confirmed ? /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement(CaveatBanner, {
    status: "warn",
    title: "SUSPECTED"
  }, fact.caveat)) : null, /*#__PURE__*/React.createElement("div", {
    className: "kit-fact__row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__k"
  }, "Formula"), /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__v"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__formula"
  }, fact.formula))), /*#__PURE__*/React.createElement("div", {
    className: "kit-fact__row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__k"
  }, "Source"), /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__v"
  }, fact.source)), /*#__PURE__*/React.createElement("div", {
    className: "kit-fact__row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__k"
  }, "Standard"), /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__v"
  }, fact.standard)), /*#__PURE__*/React.createElement("div", {
    className: "kit-fact__row"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__k"
  }, "Fact ID"), /*#__PURE__*/React.createElement("span", {
    className: "kit-fact__v"
  }, /*#__PURE__*/React.createElement(CitationChip, {
    id: fact.id,
    confirmed: fact.confirmed
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-narrative"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-narrative__tag"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: 3,
      background: "var(--accent)",
      display: "inline-block"
    }
  }), "AI interpretation \xB7 disclosed & grounded"), fact.narrative, /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack",
    style: {
      marginTop: 12,
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-muted",
    style: {
      fontSize: 12
    }
  }, "Grounded in"), /*#__PURE__*/React.createElement(CitationChip, {
    id: fact.id,
    confirmed: fact.confirmed
  }), /*#__PURE__*/React.createElement(CitationChip, {
    id: "UPD-0042"
  }))))))));
}
window.ActLedger = ActLedger;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActLedger.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActOrbit.jsx
try { (() => {
const {
  ProgramTile,
  CitationChip,
  MetricTile
} = window.AISMATCommandDeck_f4ddd5;
function ActOrbit({
  ctx
}) {
  const KIT = window.KIT;
  const progs = KIT.programs;
  const confettiOK = ctx.extras && !window.__aismatConfetti;
  React.useEffect(() => {
    if (confettiOK) window.__aismatConfetti = true;
  }, []);
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-orbit",
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement(window.Starfield, {
    on: ctx.starfield
  }), /*#__PURE__*/React.createElement("div", {
    className: "kit-orbit__head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Act I \xB7 Orbit \u2014 the whole portfolio, one sentence"), /*#__PURE__*/React.createElement("h1", {
    className: "kit-orbit__finding"
  }, /*#__PURE__*/React.createElement("span", {
    className: "num"
  }, "3 of 14"), " programs are trending ", /*#__PURE__*/React.createElement("span", {
    className: "red"
  }, "red"), " on critical-path health; ", /*#__PURE__*/React.createElement("b", null, "Program Falcon"), " lost ", /*#__PURE__*/React.createElement("span", {
    className: "num"
  }, "11 days"), " of float in the last update."), /*#__PURE__*/React.createElement("div", {
    className: "kit-orbit__meta"
  }, /*#__PURE__*/React.createElement(CitationChip, {
    id: "FACT-2291",
    onClick: () => ctx.setAct("ledger")
  }), /*#__PURE__*/React.createElement(CitationChip, {
    id: "FACT-3117",
    onClick: () => ctx.setAct("ledger")
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-muted"
  }, "engine-computed, never model-invented \xB7 pulsing tiles changed since Update #41"))), /*#__PURE__*/React.createElement("div", {
    className: "kit-execstrip"
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Programs trending red",
    value: /*#__PURE__*/React.createElement(window.CountUp, {
      value: 3
    }),
    valueTone: "fail",
    trendDir: "up",
    trendTone: "fail",
    delta: "+1 since last week"
  }), /*#__PURE__*/React.createElement(MetricTile, {
    label: "Float lost \xB7 worst program",
    value: /*#__PURE__*/React.createElement(window.CountUp, {
      value: 11,
      prefix: "-"
    }),
    unit: "d",
    valueTone: "fail",
    trendDir: "down",
    trendTone: "fail",
    delta: "Falcon, update #42"
  }), /*#__PURE__*/React.createElement(MetricTile, {
    label: "Portfolio DCMA-14 avg",
    value: /*#__PURE__*/React.createElement(window.CountUp, {
      value: 12.1,
      decimals: 1
    }),
    unit: "/14",
    trendDir: "up",
    trendTone: "pass",
    delta: "+0.4 since last week"
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-constellation"
  }, progs.map(p => /*#__PURE__*/React.createElement("div", {
    key: p.id,
    className: p.risk > 0.78 ? "kit-cell--lg" : "",
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement(ProgramTile, {
    name: p.name,
    health: p.health,
    changed: p.changed,
    trendDir: p.trend === "flat" ? undefined : p.trend,
    metric: (p.floatDelta > 0 ? "+" : "") + p.floatDelta + "d",
    sub: "next · " + p.next + " " + p.date,
    onClick: () => ctx.openProgram(p.id)
  }), p.dcmaPass === 14 ? /*#__PURE__*/React.createElement(window.ConfettiBurst, {
    fire: confettiOK
  }) : null))));
}
window.ActOrbit = ActOrbit;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActOrbit.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActPortfolio.jsx
try { (() => {
const {
  StatusChip,
  DcmaStrip,
  Sparkline,
  Tag,
  Input,
  Button,
  Tooltip
} = window.AISMATCommandDeck_f4ddd5;
function dcmaResults(passCount) {
  return Array.from({
    length: 14
  }, (_, i) => ({
    status: i < passCount ? "pass" : "fail"
  }));
}
function ActPortfolio({
  ctx
}) {
  const KIT = window.KIT;
  const [sort, setSort] = React.useState({
    key: "risk",
    dir: "desc"
  });
  const cols = [{
    key: "name",
    label: "Program"
  }, {
    key: "health",
    label: "Health"
  }, {
    key: "score",
    label: "Score"
  }, {
    key: "dcmaPass",
    label: "DCMA-14"
  }, {
    key: "spi",
    label: "SPI trend"
  }, {
    key: "cpi",
    label: "CPI"
  }, {
    key: "floatDelta",
    label: "Float Δ"
  }, {
    key: "next",
    label: "Next milestone"
  }];
  const sorted = [...KIT.programs].map(p => ({
    ...p,
    score: {
      falcon: 71,
      sentinel: 58,
      cascade: 66,
      vega: 78,
      meridian: 81,
      orion: 88,
      atlas: 93,
      halyard: 85,
      beacon: 91
    }[p.id]
  })).sort((a, b) => {
    const d = sort.dir === "asc" ? 1 : -1;
    const av = a[sort.key],
      bv = b[sort.key];
    return (av > bv ? 1 : av < bv ? -1 : 0) * d;
  });
  const onSort = k => setSort(s => ({
    key: k,
    dir: s.key === k && s.dir === "desc" ? "asc" : "desc"
  }));
  const healthLabel = {
    pass: "On-track",
    warn: "Watch",
    fail: "At-risk"
  };
  const SCORES = {
    falcon: 71,
    sentinel: 58,
    cascade: 66,
    vega: 78,
    meridian: 81,
    orion: 88,
    atlas: 93,
    halyard: 85,
    beacon: 91
  };
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acthead"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Act II \xB7 Portfolio"), /*#__PURE__*/React.createElement("div", {
    className: "kit-acttitle"
  }, "14 programs \xB7 portfolio health"), /*#__PURE__*/React.createElement("div", {
    className: "kit-actsub"
  }, "Dense, sortable, fast \u2014 the Power BI moment. Every column sorts, and every column header explains itself on hover. Click a row to zoom into its deep-dive.")), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "download",
    size: "sm"
  }, "Export table")), /*#__PURE__*/React.createElement("div", {
    className: "kit-filters"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 240
    }
  }, /*#__PURE__*/React.createElement(Input, {
    prefixIcon: "filter",
    placeholder: "Filter programs\u2026",
    size: "sm"
  })), /*#__PURE__*/React.createElement(Tag, {
    onRemove: () => {}
  }, "Float < 5d"), /*#__PURE__*/React.createElement(Tag, {
    onRemove: () => {}
  }, "DCMA < 12/14"), /*#__PURE__*/React.createElement(Tag, {
    icon: "bookmark"
  }, "Saved view \xB7 weekly review"), /*#__PURE__*/React.createElement("span", {
    className: "kit-muted",
    style: {
      fontSize: 13
    }
  }, "\xB7 PM view \u2014 milestones & float first")), /*#__PURE__*/React.createElement("div", {
    className: "kit-tablewrap"
  }, /*#__PURE__*/React.createElement("table", {
    className: "kit-table"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, cols.map(c => /*#__PURE__*/React.createElement("th", {
    key: c.key,
    onClick: () => onSort(c.key)
  }, /*#__PURE__*/React.createElement(Tooltip, {
    placement: "bottom",
    dwell: 500,
    content: KIT.colExplain[c.key]
  }, /*#__PURE__*/React.createElement("span", null, c.label)), /*#__PURE__*/React.createElement("span", {
    className: "kit-sort"
  }, sort.key === c.key ? sort.dir === "asc" ? "▲" : "▼" : "↕"))))), /*#__PURE__*/React.createElement("tbody", null, sorted.map(p => /*#__PURE__*/React.createElement("tr", {
    key: p.id,
    onClick: () => ctx.openProgram(p.id)
  }, /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("span", {
    className: "kit-progname"
  }, /*#__PURE__*/React.createElement("span", {
    className: "aismat-progtile__health aismat-progtile__health--" + p.health
  }), p.name)), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement(StatusChip, {
    status: p.health
  }, healthLabel[p.health])), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono",
    style: {
      color: p.score >= 80 ? "var(--status-pass)" : p.score >= 60 ? "var(--status-warn)" : "var(--status-fail)"
    }
  }, p.score), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack"
  }, /*#__PURE__*/React.createElement(DcmaStrip, {
    results: dcmaResults(p.dcmaPass),
    showIndex: false
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-mono kit-muted",
    style: {
      fontSize: 12
    }
  }, p.dcmaPass, "/14"))), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack"
  }, /*#__PURE__*/React.createElement(Sparkline, {
    data: p.spark,
    width: 68,
    height: 22,
    color: p.spi < 1 ? "var(--status-fail)" : "var(--status-pass)",
    animate: false
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-mono"
  }, p.spi.toFixed(2)))), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono"
  }, p.cpi.toFixed(2)), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono",
    style: {
      color: p.floatDelta < 0 ? "var(--status-fail)" : p.floatDelta > 0 ? "var(--status-pass)" : "var(--text-muted)"
    }
  }, (p.floatDelta > 0 ? "+" : "") + p.floatDelta, "d"), /*#__PURE__*/React.createElement("td", null, p.next, " ", /*#__PURE__*/React.createElement("span", {
    className: "kit-muted"
  }, "\xB7 ", p.date))))))));
}
window.ActPortfolio = ActPortfolio;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActPortfolio.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/ActRisk.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  InstrumentPanel,
  MetricTile,
  CaveatBanner,
  StatusChip,
  Button,
  Icon
} = window.AISMATCommandDeck_f4ddd5;
function ActRisk({
  ctx
}) {
  const KIT = window.KIT;
  const mc = KIT.mc;
  const maxC = Math.max(...mc.counts);
  const [explain, setExplain] = React.useState(null);
  const [depth, setDepth] = React.useState(null);
  const p50i = mc.bins.indexOf(mc.p50),
    p80i = mc.bins.indexOf(mc.p80);
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acthead"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-acteyebrow"
  }, "Role station \xB7 Risk Manager"), /*#__PURE__*/React.createElement("div", {
    className: "kit-acttitle"
  }, "Schedule risk analysis \u2014 Falcon"), /*#__PURE__*/React.createElement("div", {
    className: "kit-actsub"
  }, "SRA-centric: the risk register, the 3-point/Monte-Carlo completion distribution, and the template-driven intake. Same engine facts, risk-first emphasis.")), /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack"
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    iconLeft: "download",
    size: "sm"
  }, "Download SRA template"), /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    iconLeft: "upload",
    size: "sm"
  }, "Upload filled register"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement(CaveatBanner, {
    status: "info",
    title: "UNVERIFIED CAPABILITY"
  }, "Monte-Carlo / 3-point simulation is unverified against the current engine \u2014 confirm with SCHED/BRAIN before promising it externally. The distribution below is illustrative of the intended instrument.")), /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-7"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Completion-date distribution",
    flag: "SUSPECTED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "P80 completion is ", /*#__PURE__*/React.createElement("b", null, mc.p80), " \u2014 three weeks past the deterministic date of ", mc.deterministic, "."),
    legend: [{
      label: "Simulated finishes (1,000 runs)",
      color: "var(--viz-4)"
    }, {
      label: "P50 / P80",
      color: "var(--accent)"
    }],
    onExplain: () => setExplain({
      title: "Completion-date distribution",
      what: "How often the simulated project finished in each week, across 1,000 Monte-Carlo runs of the network with 3-point durations.",
      how: "Each run samples every risk-loaded activity's duration from its optimistic/most-likely/pessimistic estimate, then re-runs CPM.",
      eg: "Commit to the P80, not the deterministic date: promising Sep 22 when P80 says Oct 13 means an 80% chance of explaining a slip later."
    }),
    onExpand: () => setDepth({
      title: "Distribution — full data",
      sub: "1,000 runs · illustrative",
      columns: [{
        key: "band",
        label: "Week of",
        mono: true
      }, {
        key: "count",
        label: "Runs (%)",
        mono: true
      }],
      rows: mc.bins.map((b, i) => ({
        band: b,
        count: mc.counts[i] + "%"
      }))
    })
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-hist",
    style: {
      height: 150
    }
  }, mc.bins.map((b, i) => /*#__PURE__*/React.createElement("div", {
    className: "kit-hist__col",
    key: b
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-hist__n"
  }, i === p50i ? /*#__PURE__*/React.createElement("span", {
    className: "kit-p-marker"
  }, "P50") : i === p80i ? /*#__PURE__*/React.createElement("span", {
    className: "kit-p-marker"
  }, "P80") : mc.counts[i]), /*#__PURE__*/React.createElement("div", {
    className: "kit-hist__bar",
    style: {
      height: mc.counts[i] / maxC * 100 + "%",
      background: i === p50i || i === p80i ? "var(--accent)" : "var(--viz-4)",
      boxShadow: i === p80i ? "var(--glow-cyan)" : "none"
    }
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-hist__lab"
  }, b)))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-5"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 14
    }
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "P80 vs deterministic",
    value: "+15",
    unit: "wd",
    valueTone: "warn",
    trendDir: "up",
    trendTone: "warn",
    delta: "gap widened 3d this update",
    flag: "SUSPECTED"
  }), /*#__PURE__*/React.createElement(MetricTile, {
    label: "Register exposure (\u03A3P\xD7I)",
    value: "16.8",
    unit: "d",
    valueTone: "fail",
    trendDir: "up",
    trendTone: "fail",
    delta: "+2.1d vs #41",
    flag: "CONFIRMED"
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Risk register \u2014 top schedule drivers",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Two risks carry ", /*#__PURE__*/React.createElement("b", null, "70% of the exposure"), " \u2014 both sit on the driving path through Building envelope."),
    onExplain: () => setExplain({
      title: "Risk register",
      what: "The active schedule risks, ranked by exposure (probability × schedule impact).",
      how: "Entries come from the SRA template round-trip; exposure is P×I in workdays.",
      eg: "Buy down the top two (pre-book the envelope crew, expedite switchgear) and the P80 pulls in by roughly two weeks — cheaper than any acceleration claim later."
    }),
    onExpand: () => setDepth({
      title: "Risk register — all",
      sub: "SRA intake · update #42",
      columns: [{
        key: "id",
        label: "ID",
        mono: true
      }, {
        key: "name",
        label: "Risk"
      }, {
        key: "p",
        label: "P",
        mono: true
      }, {
        key: "impact",
        label: "Impact",
        mono: true
      }, {
        key: "exposure",
        label: "Exposure",
        mono: true
      }, {
        key: "owner",
        label: "Owner"
      }],
      rows: KIT.risks
    })
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-tablewrap kit-risktable"
  }, /*#__PURE__*/React.createElement("table", {
    className: "kit-table"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "ID"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Risk"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Probability"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Impact"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Exposure"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Owner"), /*#__PURE__*/React.createElement("th", {
    style: {
      cursor: "default"
    }
  }, "Severity"))), /*#__PURE__*/React.createElement("tbody", null, KIT.risks.map(r => /*#__PURE__*/React.createElement("tr", {
    key: r.id,
    style: {
      cursor: "default"
    }
  }, /*#__PURE__*/React.createElement("td", {
    className: "kit-mono"
  }, r.id), /*#__PURE__*/React.createElement("td", {
    style: {
      color: "var(--text-primary)"
    }
  }, r.name), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono"
  }, r.p), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono"
  }, r.impact), /*#__PURE__*/React.createElement("td", {
    className: "kit-mono"
  }, r.exposure), /*#__PURE__*/React.createElement("td", null, r.owner), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement(StatusChip, {
    status: r.tone
  }, r.tone === "fail" ? "Major" : r.tone === "warn" ? "Moderate" : "Minor")))))))))), /*#__PURE__*/React.createElement(window.DepthDialog, _extends({
    open: !!depth,
    onClose: () => setDepth(null)
  }, depth || {})), /*#__PURE__*/React.createElement(window.ExplainDialog, {
    open: !!explain,
    onClose: () => setExplain(null),
    ex: explain
  }));
}
window.ActRisk = ActRisk;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/ActRisk.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/DeepDiveEVM.jsx
try { (() => {
/* Deep-Dive · EVM tab — full ANSI/EIA-748 metric set + S-curve + earned schedule. */
const {
  InstrumentPanel,
  MetricTile,
  Tooltip,
  TrendChart
} = window.AISMATCommandDeck_f4ddd5;
function sPts(series, maxV, w, h, pad) {
  const n = series.length;
  return series.map((v, i) => (pad + i / (n - 1) * (w - pad * 2)).toFixed(1) + "," + (h - pad - v / maxV * (h - pad * 2)).toFixed(1)).join(" ");
}
function DeepDiveEVM({
  ctx,
  setDepth,
  setExplain
}) {
  const KIT = window.KIT;
  const f = KIT.evmFull,
    evm = KIT.evm,
    tr = KIT.trends;
  const maxV = Math.max(...evm.pv) * 1.08;
  const W = 340,
    H = 150,
    P = 16;
  const noop = () => {};
  const varDepth = () => setDepth({
    title: "EVM variance — full data",
    sub: "Cumulative $M · update #42",
    columns: [{
      key: "m",
      label: "Month"
    }, {
      key: "pv",
      label: "PV",
      mono: true
    }, {
      key: "ev",
      label: "EV",
      mono: true
    }, {
      key: "ac",
      label: "AC",
      mono: true
    }, {
      key: "sv",
      label: "SV",
      mono: true
    }, {
      key: "cv",
      label: "CV",
      mono: true
    }],
    rows: evm.months.map((m, i) => ({
      m,
      pv: evm.pv[i],
      ev: evm.ev[i],
      ac: evm.ac[i],
      sv: (evm.ev[i] - evm.pv[i]).toFixed(1),
      cv: (evm.ev[i] - evm.ac[i]).toFixed(1)
    }))
  });
  const esDepth = () => setDepth({
    title: "Earned schedule — full data",
    sub: "Updates #36–#42",
    columns: [{
      key: "u",
      label: "Update",
      mono: true
    }, {
      key: "es",
      label: "ES (wk)",
      mono: true
    }, {
      key: "at",
      label: "AT (wk)",
      mono: true
    }, {
      key: "spit",
      label: "SPI(t)",
      mono: true
    }],
    rows: KIT.updates.map((u, i) => ({
      u,
      es: tr.es[i],
      at: tr.at[i],
      spit: (tr.es[i] / tr.at[i]).toFixed(2)
    }))
  });
  const T = ({
    what,
    how,
    eg,
    children
  }) => /*#__PURE__*/React.createElement(Tooltip, {
    className: "kit-ttblock",
    what: what,
    how: how,
    example: eg
  }, children);
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-metricrow"
  }, /*#__PURE__*/React.createElement(T, {
    what: "Schedule Variance — " + f.sv + " $M.",
    how: "SV = EV \u2212 PV.",
    eg: "Negative SV in money terms; pair with SPI(t) for the time answer."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Schedule Variance (SV)",
    value: f.sv.toFixed(1),
    unit: "$M",
    valueTone: "fail",
    trendDir: "down",
    trendTone: "fail",
    delta: "widening since #39",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Cost Variance — +" + f.cv + " $M.",
    how: "CV = EV \u2212 AC.",
    eg: "Positive CV: work is earning more than it costs \u2014 cost is not the fire."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Cost Variance (CV)",
    value: "+" + f.cv.toFixed(1),
    unit: "$M",
    valueTone: "pass",
    trendDir: "up",
    trendTone: "pass",
    delta: "stable",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Variance at Completion — " + f.vac + " $M.",
    how: "VAC = BAC \u2212 EAC = 150 \u2212 155.",
    eg: "Negative VAC means the budget is already spent on paper; brief the sponsor before the number briefs them."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Variance at Completion",
    value: f.vac.toFixed(0),
    unit: "$M",
    valueTone: "fail",
    trendDir: "down",
    trendTone: "fail",
    delta: "crossed zero in #40",
    flag: "SUSPECTED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Estimate to Complete — " + f.etc + " $M.",
    how: "ETC = EAC \u2212 AC = 155 \u2212 75.",
    eg: "What it still takes from here; sanity-check against remaining scope, not remaining budget."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Estimate to Complete",
    value: f.etc,
    unit: "$M",
    trendDir: "flat",
    trendTone: "neutral",
    delta: "EAC 155 \xB7 BAC 150",
    flag: "CONFIRMED"
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-metricrow",
    style: {
      marginBottom: 4
    }
  }, /*#__PURE__*/React.createElement(T, {
    what: "TCPI to BAC — " + f.tcpi + ".",
    how: "(BAC \u2212 EV) \xF7 (BAC \u2212 AC).",
    eg: "Needing 1.08 efficiency from a team performing at 1.04 is a stretch; above ~1.10 it's fiction."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "TCPI (to BAC)",
    value: f.tcpi.toFixed(2),
    valueTone: "warn",
    trendDir: "up",
    trendTone: "warn",
    delta: "above CPI \u2014 at risk",
    flag: "SUSPECTED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Earned-schedule SPI(t) — " + f.spit.toFixed(2) + ".",
    how: "ES \xF7 AT: schedule performance in TIME units, immune to SPI's end-of-project drift to 1.0.",
    eg: "SPI(t) 0.90 = every planned 10 weeks delivers 9. Trust this over SPI late in a program."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "SPI(t) \xB7 earned schedule",
    value: f.spit.toFixed(2),
    valueTone: "fail",
    trendDir: "down",
    trendTone: "fail",
    delta: "ES 19.8wk / AT 22wk",
    flag: "SUSPECTED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Baseline Execution Index — " + f.bei + ".",
    how: "Tasks completed \xF7 tasks baselined to complete by now.",
    eg: "BEI below 0.95 with SPI near 1.0 usually means earning is front-loaded \u2014 check the earning rules."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Baseline Execution Index",
    value: f.bei.toFixed(2),
    valueTone: "warn",
    trendDir: "flat",
    trendTone: "warn",
    delta: "94 of 100 planned done",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Critical Path Length Index — " + f.cpli + ".",
    how: "(CP length + total float) \xF7 CP length.",
    eg: "CPLI under 1.00 says the critical path itself can no longer absorb any slip \u2014 recovery must add capacity, not hope."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "CPLI",
    value: f.cpli.toFixed(2),
    valueTone: "warn",
    trendDir: "down",
    trendTone: "warn",
    delta: "DCMA check 14",
    flag: "CONFIRMED"
  })))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-7"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "S-curve \xB7 PV / EV / AC",
    flag: "SUSPECTED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Earned value tracks ", /*#__PURE__*/React.createElement("b", null, "below plan, above cost"), " \u2014 the classic float-for-burn-rate trade."),
    legend: [{
      label: "PV (planned)",
      color: "var(--viz-3)"
    }, {
      label: "EV (earned)",
      color: "var(--viz-1)"
    }, {
      label: "AC (actual)",
      color: "var(--viz-2)"
    }],
    onExplain: () => setExplain({
      title: "S-curve",
      what: "Cumulative planned value, earned value, and actual cost.",
      how: "PV/EV/AC per ANSI/EIA-748 from the cost-loaded schedule.",
      eg: "The vertical gap EV→PV is schedule variance in dollars; the gap EV→AC is cost variance. Watch the gaps' direction, not their size."
    }),
    onGrid: varDepth,
    onDownload: noop,
    onExpand: varDepth
  }, /*#__PURE__*/React.createElement("svg", {
    className: "kit-chart",
    viewBox: "0 0 " + W + " " + H,
    style: {
      height: 170
    }
  }, [0, 0.25, 0.5, 0.75, 1].map((g, i) => /*#__PURE__*/React.createElement("line", {
    key: i,
    x1: P,
    x2: W - P,
    y1: H - P - g * (H - P * 2),
    y2: H - P - g * (H - P * 2),
    stroke: "var(--grid-line)",
    strokeWidth: "1",
    vectorEffect: "non-scaling-stroke"
  })), /*#__PURE__*/React.createElement("polyline", {
    points: sPts(evm.pv, maxV, W, H, P),
    fill: "none",
    stroke: "var(--viz-3)",
    strokeWidth: "2",
    strokeDasharray: "4 3",
    vectorEffect: "non-scaling-stroke"
  }), /*#__PURE__*/React.createElement("polyline", {
    points: sPts(evm.ac, maxV, W, H, P),
    fill: "none",
    stroke: "var(--viz-2)",
    strokeWidth: "2",
    vectorEffect: "non-scaling-stroke"
  }), /*#__PURE__*/React.createElement("polyline", {
    points: sPts(evm.ev, maxV, W, H, P),
    fill: "none",
    stroke: "var(--viz-1)",
    strokeWidth: "2.5",
    vectorEffect: "non-scaling-stroke"
  }), evm.months.map((m, i) => /*#__PURE__*/React.createElement("text", {
    key: i,
    x: P + i / (evm.months.length - 1) * (W - P * 2),
    y: H - 3,
    fill: "var(--text-faint)",
    fontSize: "9",
    fontFamily: "'IBM Plex Mono', monospace",
    textAnchor: "middle"
  }, m))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-5"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Earned schedule overlay",
    flag: "SUSPECTED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Earned schedule lags actual time by ", /*#__PURE__*/React.createElement("b", null, "2.2 weeks"), " \u2014 SPI(t) 0.90 and flat."),
    legend: [{
      label: "ES — earned schedule (wk)",
      color: "var(--viz-1)"
    }, {
      label: "AT — actual time (wk)",
      color: "var(--baseline-line)"
    }],
    onExplain: () => setExplain({
      title: "Earned schedule",
      what: "How many weeks of the PLAN have been earned (ES) versus weeks elapsed (AT).",
      how: "ES is where the PV curve reaches today's EV; SPI(t) = ES ÷ AT.",
      eg: "Unlike SPI, SPI(t) doesn't drift to 1.0 as the job ends — it's the honest late-program schedule metric for claims and forecasts."
    }),
    onGrid: esDepth,
    onDownload: noop,
    onExpand: esDepth
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.updates,
    series: [{
      label: "ES",
      color: "var(--viz-1)",
      data: tr.es
    }, {
      label: "AT",
      color: "var(--baseline-line)",
      data: tr.at,
      dashed: true
    }],
    yFormat: v => Math.round(v) + "wk",
    height: 168
  }))));
}
window.DeepDiveEVM = DeepDiveEVM;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/DeepDiveEVM.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/DeepDiveForensics.jsx
try { (() => {
/* Deep-Dive · Forensics tab — manipulation detection, windows analysis,
   delay responsibility matrix, critical-path shift log. */
const {
  InstrumentPanel,
  MetricTile,
  CaveatBanner,
  StatusChip,
  Badge
} = window.AISMATCommandDeck_f4ddd5;
function DeepDiveForensics({
  ctx,
  setDepth,
  setExplain
}) {
  const KIT = window.KIT;
  const fo = KIT.forensics;
  const maxW = Math.max(...fo.windows.map(w => w.d));
  const noop = () => {};
  const winDepth = () => setDepth({
    title: "Windows analysis — full data",
    sub: "Contemporaneous period analysis · AACE RP 29R-03",
    columns: [{
      key: "win",
      label: "Window",
      mono: true
    }, {
      key: "d",
      label: "Delay (d)",
      mono: true
    }, {
      key: "resp",
      label: "Responsibility"
    }],
    rows: fo.windows
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(CaveatBanner, {
    status: "info",
    title: "METHODOLOGY NOTE"
  }, "Windows (contemporaneous period) analysis per AACE RP 29R-03; apportionment here is illustrative fixture data. Every figure below cites its window and update in the ledger.")), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-5"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Manipulation detection",
    flag: "SUSPECTED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Risk score ", /*#__PURE__*/React.createElement("b", null, "62 \u2014 ELEVATED"), ": hard constraints and duration cuts landed on the driving path between #40 and #42."),
    onExplain: () => setExplain({
      title: "Manipulation risk score",
      what: "A weighted 0–100 pattern score over changes between updates: logic edits, constraint changes, duration gaming, float insertion, out-of-sequence progress, phantom activities.",
      how: "Each pattern is detected by diffing consecutive updates activity-by-activity; weights favor changes that touch the driving path.",
      eg: "A score isn't an accusation — it's a reading list. Start with the two FAIL patterns and ask the scheduler for the change narrative; innocent edits have paper trails."
    }),
    onGrid: () => setDepth({
      title: "Manipulation patterns",
      sub: "Diff #40→#42",
      columns: [{
        key: "name",
        label: "Pattern"
      }, {
        key: "detail",
        label: "Finding"
      }, {
        key: "status",
        label: "Severity"
      }],
      rows: fo.patterns
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-forscore"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-forscore__n"
  }, fo.score), /*#__PURE__*/React.createElement("span", {
    className: "kit-forscore__of"
  }, "/100 \xB7 ", fo.klass)), /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 0
    }
  }, fo.patterns.map(p => /*#__PURE__*/React.createElement("div", {
    key: p.name,
    className: "kit-pattern"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-pattern__name"
  }, p.name), /*#__PURE__*/React.createElement("div", {
    className: "kit-pattern__detail"
  }, p.detail)), /*#__PURE__*/React.createElement(StatusChip, {
    status: p.status
  }, p.status === "fail" ? "Flag" : p.status === "warn" ? "Watch" : "Clean")))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-7"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Windows analysis \u2014 delay per period",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "17 days of delay across six windows; ", /*#__PURE__*/React.createElement("b", null, "9 sit with the contractor"), ", concentrated in #41\u2192#42."),
    legend: [{
      label: "Owner",
      color: "var(--status-info)"
    }, {
      label: "Contractor",
      color: "var(--status-fail)"
    }, {
      label: "Concurrent",
      color: "var(--viz-4)"
    }, {
      label: "Force majeure",
      color: "var(--status-neutral)"
    }],
    onExplain: () => setExplain({
      title: "Windows analysis",
      what: "Project delay measured window-by-window between consecutive updates, each window's delay assigned a responsibility.",
      how: "For each window, the finish-date movement is measured against the contemporaneous schedule and apportioned by cause (AACE RP 29R-03 §windows).",
      eg: "Windows beats a single end-of-job comparison because it catches concurrency: the #39→#40 storm window is force majeure even though the contractor was also late in #41→#42."
    }),
    onGrid: winDepth,
    onDownload: noop,
    onExpand: winDepth
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-hist",
    style: {
      height: 140
    }
  }, fo.windows.map(w => /*#__PURE__*/React.createElement("div", {
    className: "kit-hist__col",
    key: w.win
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-hist__n"
  }, w.d, "d"), /*#__PURE__*/React.createElement("div", {
    className: "kit-hist__bar",
    style: {
      height: w.d / maxW * 100 + "%",
      background: fo.respColors[w.resp]
    },
    title: w.resp
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-hist__lab"
  }, w.win)))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-metricrow"
  }, fo.matrix.map(([who, d, tone]) => /*#__PURE__*/React.createElement(MetricTile, {
    key: who,
    label: "Delay · " + who,
    value: d,
    unit: "d",
    valueTone: tone === "neutral" ? undefined : tone === "info" ? undefined : tone,
    trendDir: who === "Contractor" ? "up" : "flat",
    trendTone: tone === "fail" ? "fail" : "neutral",
    delta: who === "Concurrent" ? "each independently critical" : who === "Force majeure" ? "excusable, non-compensable" : "of 17d total",
    flag: "CONFIRMED"
  })))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-12"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Critical-path shift log",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "The driving path has shifted ", /*#__PURE__*/React.createElement("b", null, "twice in seven updates"), " \u2014 both shifts trace to the Building envelope chain."),
    onExplain: () => setExplain({
      title: "Critical-path shift log",
      what: "Every update where the longest path changed membership, with the cause.",
      how: "Longest-path comparison between consecutive updates; near-critical (<2d) chains are tracked too.",
      eg: "A path that shifts every update is either a volatile job or a managed narrative. Cross-check each shift against the manipulation patterns above."
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 0
    }
  }, fo.cpShift.map(s => /*#__PURE__*/React.createElement("div", {
    key: s.upd,
    className: "kit-shiftrow"
  }, /*#__PURE__*/React.createElement(Badge, {
    tone: "accent"
  }, s.upd), /*#__PURE__*/React.createElement("span", null, s.text)))))));
}
window.DeepDiveForensics = DeepDiveForensics;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/DeepDiveForensics.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/DeepDiveQuality.jsx
try { (() => {
/* Deep-Dive · Quality tab — Schedule Health Score, logic/constraint density,
   open ends, lags, out-of-sequence, resources. */
const {
  InstrumentPanel,
  MetricTile,
  Tooltip,
  TrendChart,
  StatusChip
} = window.AISMATCommandDeck_f4ddd5;
function HealthGauge({
  score
}) {
  const tone = score >= 80 ? "var(--status-pass)" : score >= 60 ? "var(--status-warn)" : "var(--status-fail)";
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-gauge"
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 200 110"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M 18 100 A 82 82 0 0 1 182 100",
    fill: "none",
    stroke: "var(--surface-hover)",
    strokeWidth: "13",
    strokeLinecap: "round"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M 18 100 A 82 82 0 0 1 182 100",
    fill: "none",
    stroke: tone,
    strokeWidth: "13",
    strokeLinecap: "round",
    pathLength: "100",
    strokeDasharray: score + " 100",
    className: "aismat-spark__line aismat-spark__line--animate",
    style: {
      "--trend-length": score
    }
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-gauge__num",
    style: {
      color: tone
    }
  }, score), /*#__PURE__*/React.createElement("div", {
    className: "kit-gauge__cap"
  }, "Schedule health \xB7 0\u2013100"), /*#__PURE__*/React.createElement("div", {
    className: "kit-gauge__ticks"
  }, /*#__PURE__*/React.createElement("span", null, "0"), /*#__PURE__*/React.createElement("span", null, "defensible \u2265 80"), /*#__PURE__*/React.createElement("span", null, "100")));
}
function DeepDiveQuality({
  ctx,
  setDepth,
  setExplain
}) {
  const KIT = window.KIT;
  const q = KIT.quality;
  const noop = () => {};
  const T = ({
    what,
    how,
    eg,
    children
  }) => /*#__PURE__*/React.createElement(Tooltip, {
    className: "kit-ttblock",
    what: what,
    how: how,
    example: eg
  }, children);
  const conDepth = () => setDepth({
    title: "Constraints — by type",
    sub: "Update #42 · 15 total",
    columns: [{
      key: "type",
      label: "Constraint type"
    }, {
      key: "n",
      label: "Count",
      mono: true
    }, {
      key: "kind",
      label: "Class"
    }],
    rows: q.constraints.map(c => ({
      ...c,
      kind: c.kind === "fail" ? "Hard — overrides logic" : "Soft"
    }))
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-panelgrid"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-col-4"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Schedule health score",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("b", null, "71/100"), " \u2014 usable, not yet defensible. Hard constraints and negative float are the deductions."),
    onExplain: () => setExplain({
      title: "Schedule health score",
      what: "A weighted 0–100 roll-up of quality deficiencies: missing logic, constraints, negative float, lags, out-of-sequence progress.",
      how: "Each deficiency class carries a weight; the score is 100 minus the weighted count, computed per update.",
      eg: "Below 60, stop debating dates — the network itself can't support them. 60–80: fix quality in parallel. 80+: the schedule can survive an opposing expert."
    }),
    onExpand: conDepth
  }, /*#__PURE__*/React.createElement(HealthGauge, {
    score: q.healthScore
  }))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-8"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-qtiles",
    style: {
      marginBottom: 12
    }
  }, /*#__PURE__*/React.createElement(T, {
    what: "8 open ends \u2014 3 activities with no predecessor, 5 with no successor.",
    how: "Network scan for missing logic (DCMA check 1 feeds this).",
    eg: "Every open end is a place delay can hide: an activity with no successor can slip forever without moving the finish date \u2014 on paper."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Open ends",
    value: "8",
    valueTone: "fail",
    trendDir: "down",
    trendTone: "pass",
    delta: "-3 vs #41",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Constraint density 4.1% \u2014 15 constrained of 366 activities.",
    how: "count(constrained) \xF7 count(incomplete).",
    eg: "Above ~5% the network stops being logic-driven; dates come from pins, not from the work."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Constraint density",
    value: "4.1",
    unit: "%",
    valueTone: "warn",
    trendDir: "up",
    trendTone: "warn",
    delta: "+2 hard since #41",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "Logic density 1.9 relationships per activity.",
    how: "count(relationships) \xF7 count(activities).",
    eg: "Healthy CPM networks run ~2.0+. Under 1.5, the schedule is a list wearing a Gantt costume."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Logic density",
    value: "1.9",
    unit: "rel/act",
    valueTone: "pass",
    trendDir: "up",
    trendTone: "pass",
    delta: "+0.1 vs #41",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "7 lags greater than 5 days.",
    how: "Scan of relationship lags (DCMA check 3).",
    eg: "A 15-day lag is usually a hidden activity \u2014 name the work instead, so it can be statused and audited."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Lags > 5d",
    value: "7",
    valueTone: "warn",
    trendDir: "flat",
    trendTone: "neutral",
    delta: "worst: 15d FS lag",
    flag: "CONFIRMED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "12 activities progressed out of sequence.",
    how: "Actual dates vs predecessor logic; retained-logic vs progress-override flagged per activity.",
    eg: "OOS progress quietly rewrites the network. Under progress-override it can hide a delay entirely \u2014 a forensic red flag."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "Out-of-sequence",
    value: "12",
    valueTone: "warn",
    trendDir: "up",
    trendTone: "warn",
    delta: "+4 vs #41",
    flag: "SUSPECTED"
  })), /*#__PURE__*/React.createElement(T, {
    what: "4 activities with duration > 44 workdays.",
    how: "DCMA check 9 threshold on remaining duration.",
    eg: "Long bars are unmanageable \u2014 break them down until each fits inside one update cycle."
  }, /*#__PURE__*/React.createElement(MetricTile, {
    label: "High duration",
    value: "4",
    valueTone: "pass",
    trendDir: "down",
    trendTone: "pass",
    delta: "-2 vs #41",
    flag: "CONFIRMED"
  })))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-5"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Constraints \u2014 by type",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Three ", /*#__PURE__*/React.createElement("b", null, "hard constraints"), " override network logic on the driving path \u2014 remove them first."),
    onExplain: () => setExplain({
      title: "Constraint breakdown",
      what: "Every date constraint in the network, grouped by type and hardness.",
      how: "Parsed from the update; hard types (MSO/MFO/hard SNET) override CPM logic, soft types only limit it.",
      eg: "A Must-Finish-On pinned to a contract date makes float read healthy while the work is drowning — the single most common way a schedule lies."
    }),
    onGrid: conDepth,
    onExpand: conDepth
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 0
    }
  }, q.constraints.map(c => /*#__PURE__*/React.createElement("div", {
    key: c.type,
    className: "kit-pattern"
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-pattern__name"
  }, c.type)), /*#__PURE__*/React.createElement("div", {
    className: "kit-hstack",
    style: {
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-mono",
    style: {
      fontSize: 13,
      color: "var(--text-secondary)"
    }
  }, c.n), /*#__PURE__*/React.createElement(StatusChip, {
    status: c.kind
  }, c.kind === "fail" ? "Hard" : "Soft"))))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-col-7"
  }, /*#__PURE__*/React.createElement(InstrumentPanel, {
    title: "Resource loading",
    flag: "CONFIRMED",
    takeaway: /*#__PURE__*/React.createElement(React.Fragment, null, "Labor demand crossed ", /*#__PURE__*/React.createElement("b", null, "capacity in May"), " \u2014 the envelope slip traces to a resource wall, not logic."),
    legend: [{
      label: "Labor demand (heads)",
      color: "var(--viz-3)"
    }, {
      label: "Capacity",
      color: "var(--status-warn)"
    }],
    onExplain: () => setExplain({
      title: "Resource loading",
      what: "Total assigned labor per period against available capacity.",
      how: "Resource assignments summed per period from the loaded schedule.",
      eg: "Demand above the capacity line means the dates assume people you don't have — level the peak or the CPM dates are aspiration."
    }),
    onGrid: () => setDepth({
      title: "Resource loading — data",
      sub: "Heads per month",
      columns: [{
        key: "m",
        label: "Month"
      }, {
        key: "labor",
        label: "Demand",
        mono: true
      }, {
        key: "cap",
        label: "Capacity",
        mono: true
      }],
      rows: KIT.evm.months.map((m, i) => ({
        m,
        labor: q.resources.labor[i],
        cap: q.resources.capacity
      }))
    }),
    onDownload: noop,
    onExpand: noop
  }, /*#__PURE__*/React.createElement(TrendChart, {
    labels: KIT.evm.months,
    series: [{
      label: "Demand",
      color: "var(--viz-3)",
      data: q.resources.labor
    }],
    hline: {
      value: q.resources.capacity,
      label: "capacity",
      color: "var(--status-warn)"
    },
    yFormat: v => Math.round(v) + "",
    height: 168
  }))));
}
window.DeepDiveQuality = DeepDiveQuality;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/DeepDiveQuality.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/KitBits.jsx
try { (() => {
/* Kit support pieces shared by all acts. Loaded BEFORE the acts. */
const {
  Dialog,
  Input,
  Button
} = window.AISMATCommandDeck_f4ddd5;

/* Animated count-up for headline numbers (respects reduced-motion). */
function CountUp({
  value,
  decimals = 0,
  prefix = "",
  suffix = "",
  duration = 900
}) {
  const [v, setV] = React.useState(0);
  React.useEffect(() => {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setV(value);
      return;
    }
    let raf;
    const t0 = performance.now();
    const tick = t => {
      const p = Math.min(1, (t - t0) / duration);
      const e = 1 - Math.pow(1 - p, 3);
      setV(value * e);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return /*#__PURE__*/React.createElement("span", null, prefix, v.toFixed(decimals), suffix);
}

/* Depth-on-demand: the ⛶ expand target — full data table + filter. */
function DepthDialog({
  open,
  onClose,
  title,
  sub,
  columns = [],
  rows = []
}) {
  const [q, setQ] = React.useState("");
  React.useEffect(() => {
    if (open) setQ("");
  }, [open]);
  const shown = rows.filter(r => !q || columns.some(c => String(r[c.key]).toLowerCase().includes(q.toLowerCase())));
  return /*#__PURE__*/React.createElement(Dialog, {
    open: open,
    onClose: onClose,
    title: title,
    subtitle: sub,
    className: "kit-dlg-wide",
    footer: /*#__PURE__*/React.createElement(Button, {
      variant: "secondary",
      iconLeft: "download",
      onClick: onClose
    }, "Export table")
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 12
    }
  }, /*#__PURE__*/React.createElement(Input, {
    prefixIcon: "filter",
    placeholder: "Filter rows\u2026",
    size: "sm",
    value: q,
    onChange: e => setQ(e.target.value)
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-tablewrap"
  }, /*#__PURE__*/React.createElement("table", {
    className: "kit-table"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, columns.map(c => /*#__PURE__*/React.createElement("th", {
    key: c.key,
    style: {
      cursor: "default"
    }
  }, c.label)))), /*#__PURE__*/React.createElement("tbody", null, shown.map((r, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      cursor: "default"
    }
  }, columns.map(c => /*#__PURE__*/React.createElement("td", {
    key: c.key,
    className: c.mono ? "kit-mono" : ""
  }, r[c.key]))))))), /*#__PURE__*/React.createElement("div", {
    className: "kit-muted",
    style: {
      fontSize: 12,
      marginTop: 10
    }
  }, shown.length, " of ", rows.length, " rows \xB7 values identical to the on-screen instrument."));
}

/* "How to read this" — the _explain() layer: what / how / real-world use. */
function ExplainDialog({
  open,
  onClose,
  ex
}) {
  if (!ex) return null;
  return /*#__PURE__*/React.createElement(Dialog, {
    open: open,
    onClose: onClose,
    title: ex.title,
    subtitle: "How to read this instrument"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-vstack",
    style: {
      gap: 14,
      paddingBottom: 6
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-exk"
  }, "What it shows"), /*#__PURE__*/React.createElement("div", {
    className: "kit-exv"
  }, ex.what)), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-exk"
  }, "How it's computed"), /*#__PURE__*/React.createElement("div", {
    className: "kit-exv"
  }, ex.how)), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "kit-exk"
  }, "Real-world read"), /*#__PURE__*/React.createElement("div", {
    className: "kit-exv"
  }, ex.eg))));
}

/* One-shot confetti burst (canvas particles, brand colors — never emoji). */
function ConfettiBurst({
  fire
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!fire || !ref.current) return;
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const cv = ref.current,
      ctx = cv.getContext("2d");
    const w = cv.width = cv.offsetWidth,
      h = cv.height = cv.offsetHeight;
    const colors = ["#33DECD", "#FFCB5C", "#43D585", "#6BA1FF"];
    const ps = Array.from({
      length: 36
    }, () => ({
      x: w / 2,
      y: h * 0.55,
      vx: (Math.random() - 0.5) * 5.5,
      vy: -2.5 - Math.random() * 3.5,
      s: 2 + Math.random() * 3,
      c: colors[Math.floor(Math.random() * colors.length)],
      a: 1
    }));
    let raf;
    const t0 = performance.now();
    const tick = t => {
      const el = t - t0;
      ctx.clearRect(0, 0, w, h);
      ps.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.12;
        p.a = Math.max(0, 1 - el / 1300);
        ctx.globalAlpha = p.a;
        ctx.fillStyle = p.c;
        ctx.fillRect(p.x, p.y, p.s, p.s);
      });
      if (el < 1400) raf = requestAnimationFrame(tick);else ctx.clearRect(0, 0, w, h);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [fire]);
  return /*#__PURE__*/React.createElement("canvas", {
    ref: ref,
    className: "kit-confetti",
    "aria-hidden": "true"
  });
}

/* Konami starfield — entirely pointless. Exactly the point. */
function Starfield({
  on
}) {
  const stars = React.useMemo(() => Array.from({
    length: 90
  }, () => ({
    l: Math.random() * 100,
    t: Math.random() * 100,
    s: 1 + Math.random() * 2,
    d: Math.random() * 2.4
  })), []);
  if (!on) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-starfield",
    "aria-hidden": "true"
  }, stars.map((st, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      left: st.l + "%",
      top: st.t + "%",
      width: st.s,
      height: st.s,
      animationDelay: st.d + "s"
    }
  })));
}
Object.assign(window, {
  CountUp,
  DepthDialog,
  ExplainDialog,
  ConfettiBurst,
  Starfield
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/KitBits.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/Shell.jsx
try { (() => {
const {
  RoleStrip,
  AirGapIndicator,
  Icon,
  Input,
  IconButton,
  Switch,
  Toast
} = window.AISMATCommandDeck_f4ddd5;
const KIT = window.KIT;
const KIT_THEMES = [{
  id: "dark",
  icon: "moon",
  title: "Dark (default)"
}, {
  id: "bright",
  icon: "sun",
  title: "Bright"
}, {
  id: "contrast",
  icon: "contrast",
  title: "High-contrast"
}, {
  id: "console",
  icon: "terminal",
  title: "Console / Ops Deck"
}];
const KONAMI = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"];

/* Crash isolation: one broken view must never blank the whole deck. */
class ActBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      err: null
    };
  }
  static getDerivedStateFromError(err) {
    return {
      err
    };
  }
  componentDidCatch(err) {
    console.error("Act render failed:", err);
  }
  render() {
    if (this.state.err) {
      return /*#__PURE__*/React.createElement("div", {
        className: "kit-actfail",
        role: "alert"
      }, /*#__PURE__*/React.createElement("div", {
        className: "kit-actfail__title"
      }, "This view failed to render"), /*#__PURE__*/React.createElement("div", {
        className: "kit-actfail__body"
      }, "The rest of the deck is unaffected \u2014 pick another act from the sidebar. Detail: ", /*#__PURE__*/React.createElement("span", {
        className: "kit-mono"
      }, String(this.state.err && this.state.err.message || this.state.err))));
    }
    return this.props.children;
  }
}
function MissingAct({
  id
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-actfail",
    role: "alert"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-actfail__title"
  }, "View unavailable in this build"), /*#__PURE__*/React.createElement("div", {
    className: "kit-actfail__body"
  }, "\u201C", id, "\u201D didn\u2019t load its component \u2014 the rest of the deck is unaffected."));
}
function KitApp() {
  const [act, setAct] = React.useState("orbit");
  const [role, setRole] = React.useState("exec");
  const [theme, setTheme] = React.useState("dark");
  const [program, setProgram] = React.useState("falcon");
  const [density, setDensity] = React.useState("comfortable");
  const [scale, setScale] = React.useState(100);
  const [extras, setExtras] = React.useState(true);
  const [tourOpen, setTourOpen] = React.useState(() => !window.tourState().done);
  const [starfield, setStarfield] = React.useState(false);
  const [hello, setHello] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const onRole = id => {
    setRole(id);
    setAct(KIT.roleActs[id] || "orbit");
  };
  const openProgram = id => {
    setProgram(id);
    setAct("deepdive");
  };
  const ctx = {
    role,
    setRole,
    onRole,
    act,
    setAct,
    program,
    setProgram,
    openProgram,
    extras,
    density,
    starfield
  };

  /* Konami on Orbit → starfield for ~5s. Entirely pointless. Exactly the point. */
  const buf = React.useRef([]);
  React.useEffect(() => {
    const onKey = e => {
      buf.current = [...buf.current, e.key].slice(-KONAMI.length);
      if (extras && act === "orbit" && KONAMI.every((k, i) => buf.current[i] === k)) {
        setStarfield(true);
        setTimeout(() => setStarfield(false), 5200);
        buf.current = [];
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [extras, act]);

  /* Codename in global search → one greeting per session. */
  React.useEffect(() => {
    if (extras && search.trim().toLowerCase() === KIT.codename && !window.__aismatHello) {
      window.__aismatHello = true;
      setHello(true);
      const t = setTimeout(() => setHello(false), 4200);
      return () => clearTimeout(t);
    }
  }, [search, extras]);
  const ActComp = {
    orbit: window.ActOrbit,
    portfolio: window.ActPortfolio,
    deepdive: window.ActDeepDive,
    ledger: window.ActLedger,
    dataroom: window.ActDataRoom,
    risk: window.ActRisk,
    compliance: window.ActCompliance,
    ingest: window.ActIngest
  }[act];
  const flush = act === "orbit";
  const prog = KIT.programs.find(p => p.id === program) || KIT.programs[0];
  const tourDone = window.tourState().done;
  const q = search.trim().toLowerCase();
  const results = q.length >= 2 && q !== KIT.codename ? [...KIT.programs.filter(p => p.name.toLowerCase().includes(q)).map(p => ({
    icon: "folder-git-2",
    label: "Program " + p.name,
    kind: "program",
    go: () => openProgram(p.id)
  })), ...KIT.activities.filter(a => a.name.toLowerCase().includes(q)).map(a => ({
    icon: "activity",
    label: a.name,
    kind: a.id,
    go: () => openProgram("falcon")
  })), ...KIT.facts.filter(f => (f.id + " " + f.label).toLowerCase().includes(q)).map(f => ({
    icon: "file-search",
    label: f.label,
    kind: f.id,
    go: () => setAct("ledger")
  }))].slice(0, 6) : [];
  const NavItem = ({
    a
  }) => /*#__PURE__*/React.createElement("button", {
    className: "kit-navitem" + (act === a.id ? " kit-navitem--active" : ""),
    onClick: () => setAct(a.id)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: a.icon,
    size: 17
  }), /*#__PURE__*/React.createElement("span", null, a.label), /*#__PURE__*/React.createElement("span", {
    className: "kit-navitem__sub"
  }, a.sub));
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-app",
    "data-theme": theme,
    "data-density": density
  }, /*#__PURE__*/React.createElement("aside", {
    className: "kit-side"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-brand"
  }, /*#__PURE__*/React.createElement("span", {
    className: "kit-brand__mark"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ai"
  }, "AI"), "SMAT"), /*#__PURE__*/React.createElement("span", {
    className: "kit-brand__cur"
  })), /*#__PURE__*/React.createElement("nav", {
    className: "kit-nav"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-navsec"
  }, "Narrative"), KIT.acts.map(a => /*#__PURE__*/React.createElement(NavItem, {
    key: a.id,
    a: a
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-navsec"
  }, "Role stations"), KIT.stations.map(a => /*#__PURE__*/React.createElement(NavItem, {
    key: a.id,
    a: a
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-navsec"
  }, "Data"), /*#__PURE__*/React.createElement(NavItem, {
    a: {
      id: "ingest",
      label: "Ingest & updates",
      icon: "file-input",
      sub: "I/O"
    }
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-side__foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-navsec",
    style: {
      padding: "0 0 2px"
    }
  }, "Appearance"), /*#__PURE__*/React.createElement("div", {
    className: "kit-themerow"
  }, KIT_THEMES.map(t => /*#__PURE__*/React.createElement("button", {
    key: t.id,
    className: "kit-themebtn" + (theme === t.id ? " kit-themebtn--active" : ""),
    title: t.title,
    onClick: () => setTheme(t.id)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: t.icon,
    size: 15
  })))), /*#__PURE__*/React.createElement("div", {
    className: "kit-foot-row"
  }, /*#__PURE__*/React.createElement("button", {
    className: "kit-densbtn" + (density === "comfortable" ? " kit-densbtn--on" : ""),
    onClick: () => setDensity("comfortable")
  }, "Cozy"), /*#__PURE__*/React.createElement("button", {
    className: "kit-densbtn" + (density === "compact" ? " kit-densbtn--on" : ""),
    onClick: () => setDensity("compact")
  }, "Compact"), /*#__PURE__*/React.createElement("select", {
    className: "kit-scale",
    value: scale,
    onChange: e => setScale(Number(e.target.value)),
    title: "UI scale"
  }, /*#__PURE__*/React.createElement("option", {
    value: "90"
  }, "90%"), /*#__PURE__*/React.createElement("option", {
    value: "100"
  }, "100%"), /*#__PURE__*/React.createElement("option", {
    value: "110"
  }, "110%"), /*#__PURE__*/React.createElement("option", {
    value: "125"
  }, "125%"))), /*#__PURE__*/React.createElement("div", {
    className: "kit-foot-switch"
  }, /*#__PURE__*/React.createElement(Switch, {
    label: "Extras (off for exhibits)",
    checked: extras,
    onChange: e => setExtras(e.target.checked)
  })))), /*#__PURE__*/React.createElement("div", {
    className: "kit-main"
  }, /*#__PURE__*/React.createElement("header", {
    className: "kit-topbar"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-search"
  }, /*#__PURE__*/React.createElement(Input, {
    prefixIcon: "search",
    placeholder: "Search programs, activities, fact IDs\u2026",
    size: "sm",
    value: search,
    onChange: e => setSearch(e.target.value)
  }), results.length ? /*#__PURE__*/React.createElement("div", {
    className: "kit-searchpop"
  }, results.map((r, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "kit-searchrow",
    onMouseDown: () => {
      r.go();
      setSearch("");
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: r.icon,
    size: 14
  }), /*#__PURE__*/React.createElement("span", null, r.label), /*#__PURE__*/React.createElement("span", {
    className: "kit-searchrow__kind"
  }, r.kind)))) : null), /*#__PURE__*/React.createElement("div", {
    className: "kit-topbar__ctx"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "folder-git-2",
    size: 14
  }), /*#__PURE__*/React.createElement("span", null, prog.name)), /*#__PURE__*/React.createElement("span", {
    className: tourDone ? "" : "kit-guidebtn--nudge"
  }, /*#__PURE__*/React.createElement(IconButton, {
    icon: "compass",
    label: "Guided tour",
    onClick: () => setTourOpen(true)
  })), /*#__PURE__*/React.createElement("div", {
    className: "kit-topbar__spacer"
  }), /*#__PURE__*/React.createElement(RoleStrip, {
    roles: KIT.roles,
    value: role,
    onChange: onRole
  })), /*#__PURE__*/React.createElement("main", {
    className: "kit-content" + (flush ? " kit-content--flush" : ""),
    key: act,
    style: {
      zoom: scale / 100
    }
  }, /*#__PURE__*/React.createElement(ActBoundary, {
    key: act
  }, ActComp ? /*#__PURE__*/React.createElement(ActComp, {
    ctx: ctx
  }) : /*#__PURE__*/React.createElement(MissingAct, {
    id: act
  }))), /*#__PURE__*/React.createElement("footer", {
    className: "kit-status"
  }, /*#__PURE__*/React.createElement(AirGapIndicator, {
    state: "airgapped"
  }), /*#__PURE__*/React.createElement("span", null, "UPDATE ", KIT.update), /*#__PURE__*/React.createElement("span", null, "DATA DATE ", KIT.dataDate), /*#__PURE__*/React.createElement("span", {
    className: "kit-status__spacer"
  }), /*#__PURE__*/React.createElement("span", {
    className: "kit-cui"
  }, "CUI // SP-PROJ"), /*#__PURE__*/React.createElement("span", null, "THE COMMAND DECK"))), /*#__PURE__*/React.createElement(window.Tour, {
    open: tourOpen,
    onClose: () => setTourOpen(false),
    ctx: ctx
  }), hello ? /*#__PURE__*/React.createElement("div", {
    style: {
      position: "fixed",
      right: 24,
      bottom: 52,
      zIndex: 400
    }
  }, /*#__PURE__*/React.createElement(Toast, {
    status: "info",
    icon: "terminal",
    title: "Good to see you again.",
    onClose: () => setHello(false)
  }, "Console hum engaged. Once per session \u2014 back to work.")) : null);
}
window.KitApp = KitApp;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/Shell.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/Tour.jsx
try { (() => {
/* First-run story walkthrough: dismissible, resumable, narrates WHY each
   screen exists, ends by asking "what's your role?" and setting the default
   landing act. State persists in localStorage (aismat_kit_tour_v1). */
const {
  Button,
  Icon
} = window.AISMATCommandDeck_f4ddd5;
const TOUR_KEY = "aismat_kit_tour_v1";
function tourState() {
  try {
    return JSON.parse(localStorage.getItem(TOUR_KEY)) || {
      i: 0,
      done: false
    };
  } catch (e) {
    return {
      i: 0,
      done: false
    };
  }
}
function saveTour(s) {
  try {
    localStorage.setItem(TOUR_KEY, JSON.stringify(s));
  } catch (e) {}
}
const TOUR_STEPS = [{
  act: "orbit",
  kick: "The Command Deck",
  title: "Every screen leaves you smarter",
  body: "AISMAT tells your portfolio's story in five acts — from 30,000 feet down to a single float value with the citation that proves it. This tour walks one real program end to end; skip any time, resume any time.",
  eg: "A director asks \"are we okay?\" five minutes before a review. You answer in one sentence — then prove it, click by click."
}, {
  act: "orbit",
  kick: "Act I · Orbit",
  title: "One screen, one sentence",
  body: "The headline is a plain-English finding written from cited, engine-computed facts — never a model-invented number. Tiles are sized by risk and colored by trend; a tile pulses ONLY if its status changed since the last update. Motion is a signal, not decoration.",
  eg: "Falcon is large, red, and pulsing: it carries the most schedule risk AND it just got worse. That is the tile to click before your milestone review, not after."
}, {
  act: "portfolio",
  kick: "Act II · Portfolio",
  title: "The dense, sortable read",
  body: "The constellation resolves into a table: DCMA-14 quality strip, SPI sparkline, float erosion, next milestone. Every column sorts, and every column header explains itself on hover — rest your pointer on \"DCMA-14\" for a beat.",
  eg: "Sort by Float Δ. Two programs bleeding float with passing DCMA scores = real schedule pressure. One bleeding float with 9/14 DCMA = fix the schedule quality before trusting its dates."
}, {
  act: "deepdive",
  kick: "Act III · Program Deep-Dive",
  title: "Instruments, not widgets",
  body: "Every visual carries a plain-English takeaway, a legend, and the same toolbar: how-to-read, data grid, export, expand (⛶). The Gantt is standardized — Float, Driving, and Walk-path options sit in the same place on every schedule view.",
  eg: "Toggle \"Walk path\" on the Gantt: the critical path lights up bar-by-bar from data date to finish — how you show a non-scheduler what \"driving\" means without a lecture."
}, {
  act: "deepdive",
  kick: "The Guide System",
  title: "Hover anything — it teaches",
  body: "Rest your pointer on any number for about three-quarters of a second: what the value is, how it's computed, and a worked example of what to do about it. Try a float value in the Gantt's right column.",
  eg: "\"4d of float\" isn't jargon anymore: it can slip 4 workdays before eating the critical path — so watch it if the upstream driving activity is already late."
}, {
  act: "deepdive",
  kick: "Trends",
  title: "Every metric, over time",
  body: "The Trends tab charts each measure across schedule updates — float, SPI/CPI/TCPI, DCMA quality, EAC. Charts draw left-to-right so your eye tracks direction first; SUSPECTED metrics carry their caveat in plain sight, never hidden behind a clean number.",
  eg: "SPI drifting down for five straight updates while CPI holds ≈ the program is trading schedule for burn rate. That pattern is a claims exhibit waiting to happen — document it now."
}, {
  act: "deepdive",
  kick: "Quality & Forensics",
  title: "Catch the schedule lying",
  body: "The Quality tab scores the network 0–100 — open ends, constraint density, logic density, out-of-sequence progress. The Forensics tab diffs updates for manipulation patterns and runs windows analysis, apportioning each period's delay to owner, contractor, concurrent, or force majeure.",
  eg: "Duration cuts plus new hard constraints on the driving path, in the same update the float 'recovered'? That is a managed narrative, not a recovery — pull the change log before the claim window closes."
}, {
  act: "ledger",
  kick: "Act IV · Forensic Ledger",
  title: "Defend the number",
  body: "Any metric clicks through to its fact ledger: exact inputs, the formula, the standard it came from (DCMA-14, EVM, NASA Acumen), the source update — and any AI narrative, disclosed and grounded in fact IDs.",
  eg: "In a deposition: \"Where does 0.92 come from?\" You open FACT-2291 — formula, source update, standard, caveat — and read it into the record. No hand-waving."
}, {
  act: "dataroom",
  kick: "Act V · Data Room",
  title: "Nobody leaves empty-handed",
  body: "Everything you walked through exports to Excel (formulas intact), Word, and PDF — CUI-marked, numerically identical to on-screen. And it all came IN through the same doctrine: native XER, MPP, XML, XLSX, CSV ingest that loads whole or rejects with a specific reason, never silently half-loaded.",
  eg: "Monday-morning ritual: export the portfolio table to Excel, the Falcon ledger to PDF, and attach both to the weekly — the numbers can't drift because they share one export service."
}, {
  act: "orbit",
  kick: "One last thing",
  title: "What's your role?",
  body: "Same engine output, re-cut for who's reading. Your role sets your default landing act and emphasis — never the data. Pick yours; you can switch any time from the strip up top.",
  roles: true
}];
function Tour({
  open,
  onClose,
  ctx
}) {
  const [i, setI] = React.useState(() => tourState().i || 0);
  const KIT = window.KIT;
  React.useEffect(() => {
    if (!open) return;
    const st = TOUR_STEPS[Math.min(i, TOUR_STEPS.length - 1)];
    if (st && ctx.act !== st.act) ctx.setAct(st.act);
    saveTour({
      i,
      done: false
    });
  }, [open, i]);
  if (!open) return null;
  const st = TOUR_STEPS[Math.min(i, TOUR_STEPS.length - 1)];
  const finish = roleId => {
    saveTour({
      i: 0,
      done: true
    });
    if (roleId) ctx.onRole(roleId);
    onClose();
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "kit-tour",
    role: "dialog",
    "aria-label": "Guided tour"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-tour__kick"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "compass",
    size: 13
  }), st.kick, " \xB7 ", i + 1, "/", TOUR_STEPS.length), /*#__PURE__*/React.createElement("div", {
    className: "kit-tour__title"
  }, st.title), /*#__PURE__*/React.createElement("div", {
    className: "kit-tour__body"
  }, st.body), st.eg ? /*#__PURE__*/React.createElement("div", {
    className: "kit-tour__eg"
  }, /*#__PURE__*/React.createElement("b", null, "Real-world read"), st.eg) : null, st.roles ? /*#__PURE__*/React.createElement("div", {
    className: "kit-tour__roles"
  }, KIT.roles.map(r => /*#__PURE__*/React.createElement(Button, {
    key: r.id,
    variant: "secondary",
    size: "sm",
    iconLeft: r.icon,
    onClick: () => finish(r.id)
  }, r.label))) : null, /*#__PURE__*/React.createElement("div", {
    className: "kit-tour__foot"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kit-tour__dots"
  }, TOUR_STEPS.map((_, d) => /*#__PURE__*/React.createElement("span", {
    key: d,
    className: "kit-tour__dot" + (d === i ? " kit-tour__dot--on" : "")
  }))), /*#__PURE__*/React.createElement(Button, {
    variant: "ghost",
    size: "sm",
    onClick: () => {
      saveTour({
        i,
        done: false
      });
      onClose();
    }
  }, "Resume later"), i > 0 ? /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    size: "sm",
    iconLeft: "arrow-left",
    onClick: () => setI(i - 1)
  }, "Back") : null, !st.roles ? /*#__PURE__*/React.createElement(Button, {
    size: "sm",
    iconRight: "arrow-right",
    onClick: () => setI(i + 1)
  }, "Next") : /*#__PURE__*/React.createElement(Button, {
    size: "sm",
    onClick: () => finish(null)
  }, "Done")));
}
Object.assign(window, {
  Tour,
  tourState
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/Tour.jsx", error: String((e && e.message) || e) }); }

// ui_kits/aismat/data.js
try { (() => {
/* AISMAT UI kit — shared mock data. Plain script: assigns window.KIT.
   Numbers are illustrative fixtures for the recreation, not real analysis. */
window.KIT = {
  dataDate: "2026-07-13",
  update: "#42",
  codename: "smat",
  roles: [{
    id: "exec",
    label: "Executive",
    icon: "telescope"
  }, {
    id: "pm",
    label: "PM",
    icon: "clipboard-list"
  }, {
    id: "sched",
    label: "Scheduler",
    icon: "git-branch"
  }, {
    id: "evm",
    label: "EVM Analyst",
    icon: "bar-chart-3"
  }, {
    id: "legal",
    label: "Forensic / Legal",
    icon: "scale"
  }, {
    id: "risk",
    label: "Risk",
    icon: "radar"
  }, {
    id: "cui",
    label: "CUI Reviewer",
    icon: "shield-check"
  }],
  roleActs: {
    exec: "orbit",
    pm: "portfolio",
    sched: "deepdive",
    evm: "deepdive",
    legal: "ledger",
    risk: "risk",
    cui: "compliance"
  },
  acts: [{
    id: "orbit",
    label: "Orbit",
    icon: "telescope",
    sub: "Act I"
  }, {
    id: "portfolio",
    label: "Portfolio",
    icon: "layout-grid",
    sub: "Act II"
  }, {
    id: "deepdive",
    label: "Program Deep-Dive",
    icon: "gauge",
    sub: "Act III"
  }, {
    id: "ledger",
    label: "Forensic Ledger",
    icon: "file-search",
    sub: "Act IV"
  }, {
    id: "dataroom",
    label: "Data Room",
    icon: "archive",
    sub: "Act V"
  }],
  stations: [{
    id: "risk",
    label: "Risk / SRA",
    icon: "radar",
    sub: "role"
  }, {
    id: "compliance",
    label: "Compliance / CUI",
    icon: "shield-check",
    sub: "role"
  }],
  programs: [{
    id: "falcon",
    name: "Falcon",
    health: "fail",
    spi: 0.92,
    cpi: 1.04,
    floatDelta: -11,
    dcmaPass: 11,
    next: "Design freeze",
    date: "Aug 14",
    trend: "down",
    changed: true,
    risk: 0.98,
    spark: [1.02, 0.99, 0.98, 0.96, 0.94, 0.92]
  }, {
    id: "sentinel",
    name: "Sentinel",
    health: "fail",
    spi: 0.88,
    cpi: 0.97,
    floatDelta: -8,
    dcmaPass: 9,
    next: "IOT&E start",
    date: "Sep 02",
    trend: "down",
    changed: true,
    risk: 0.9,
    spark: [0.98, 0.96, 0.93, 0.9, 0.89, 0.88]
  }, {
    id: "cascade",
    name: "Cascade",
    health: "fail",
    spi: 0.9,
    cpi: 0.99,
    floatDelta: -6,
    dcmaPass: 10,
    next: "Site handover",
    date: "Aug 28",
    trend: "down",
    changed: false,
    risk: 0.82,
    spark: [0.97, 0.95, 0.94, 0.92, 0.91, 0.9]
  }, {
    id: "vega",
    name: "Vega",
    health: "warn",
    spi: 0.96,
    cpi: 1.01,
    floatDelta: -2,
    dcmaPass: 12,
    next: "CDR",
    date: "Aug 07",
    trend: "down",
    changed: true,
    risk: 0.62,
    spark: [1.0, 0.99, 0.98, 0.97, 0.96, 0.96]
  }, {
    id: "meridian",
    name: "Meridian",
    health: "warn",
    spi: 0.98,
    cpi: 1.02,
    floatDelta: 1,
    dcmaPass: 12,
    next: "LRIP",
    date: "Oct 11",
    trend: "flat",
    changed: false,
    risk: 0.5,
    spark: [0.97, 0.98, 0.98, 0.99, 0.98, 0.98]
  }, {
    id: "orion",
    name: "Orion",
    health: "pass",
    spi: 1.01,
    cpi: 1.03,
    floatDelta: 4,
    dcmaPass: 13,
    next: "PDR",
    date: "Jul 30",
    trend: "up",
    changed: false,
    risk: 0.36,
    spark: [0.98, 0.99, 1.0, 1.0, 1.01, 1.01]
  }, {
    id: "atlas",
    name: "Atlas",
    health: "pass",
    spi: 1.03,
    cpi: 1.05,
    floatDelta: 3,
    dcmaPass: 14,
    next: "Test complete",
    date: "Aug 20",
    trend: "up",
    changed: true,
    risk: 0.3,
    spark: [1.0, 1.01, 1.02, 1.02, 1.03, 1.03]
  }, {
    id: "halyard",
    name: "Halyard",
    health: "pass",
    spi: 1.0,
    cpi: 1.0,
    floatDelta: 0,
    dcmaPass: 13,
    next: "Delivery",
    date: "Nov 05",
    trend: "flat",
    changed: false,
    risk: 0.26,
    spark: [1.0, 1.0, 0.99, 1.0, 1.0, 1.0]
  }, {
    id: "beacon",
    name: "Beacon",
    health: "pass",
    spi: 1.02,
    cpi: 1.04,
    floatDelta: 6,
    dcmaPass: 14,
    next: "Closeout",
    date: "Dec 01",
    trend: "up",
    changed: false,
    risk: 0.2,
    spark: [0.99, 1.0, 1.01, 1.01, 1.02, 1.02]
  }],
  colExplain: {
    name: "The program. Click any row to zoom into its deep-dive.",
    health: "Composite critical-path health: pass = on-track, watch = near-critical float, fail = negative float or failing quality checks.",
    dcmaPass: "DCMA 14-point assessment — how many of the 14 schedule-quality checks pass. Below 12/14, treat the CPM dates as suspect.",
    spi: "Schedule Performance Index = EV ÷ PV. Below 1.00 the program is earning slower than planned; the sparkline shows the last 6 updates.",
    cpi: "Cost Performance Index = EV ÷ AC. Below 1.00 each earned dollar costs more than planned.",
    floatDelta: "Total float gained (+) or lost (−) on the driving path since the last update. Sustained loss = margin bleeding.",
    next: "Next contractual milestone and its current forecast date.",
    score: "Schedule Health Score 0–100 — weighted deficiency count across quality checks, float posture, and logic integrity. Below 60, dates are not defensible."
  },
  dcma: [{
    n: 1,
    name: "Logic",
    status: "pass"
  }, {
    n: 2,
    name: "Leads",
    status: "pass"
  }, {
    n: 3,
    name: "Lags",
    status: "warn"
  }, {
    n: 4,
    name: "Relationship types",
    status: "pass"
  }, {
    n: 5,
    name: "Hard constraints",
    status: "fail"
  }, {
    n: 6,
    name: "Soft constraints",
    status: "pass"
  }, {
    n: 7,
    name: "High float",
    status: "pass"
  }, {
    n: 8,
    name: "Negative float",
    status: "fail"
  }, {
    n: 9,
    name: "High duration",
    status: "pass"
  }, {
    n: 10,
    name: "Invalid dates",
    status: "pass"
  }, {
    n: 11,
    name: "Resources",
    status: "pass"
  }, {
    n: 12,
    name: "Missed tasks",
    status: "pass"
  }, {
    n: 13,
    name: "Critical path test",
    status: "pass"
  }, {
    n: 14,
    name: "CPLI",
    status: "pass"
  }],
  evm: {
    months: ["Feb", "Mar", "Apr", "May", "Jun", "Jul"],
    pv: [10, 22, 36, 52, 70, 88],
    ev: [9, 20, 32, 46, 62, 78],
    ac: [8, 19, 31, 44, 59, 75]
  },
  updates: ["#36", "#37", "#38", "#39", "#40", "#41", "#42"],
  trends: {
    spi: [1.04, 1.02, 0.99, 0.98, 0.96, 0.94, 0.92],
    cpi: [1.01, 1.02, 1.03, 1.03, 1.04, 1.04, 1.04],
    tcpi: [0.99, 1.0, 1.02, 1.03, 1.05, 1.06, 1.08],
    floatTotal: [22, 20, 19, 15, 13, 11, 4],
    dcmaPass: [9, 9, 10, 10, 10, 9, 11],
    eac: [146, 147, 149, 151, 152, 153, 155],
    es: [10.5, 12.2, 13.8, 15.4, 16.9, 18.4, 19.8],
    at: [10, 12, 14, 16, 18, 20, 22],
    bac: 150
  },
  floatHist: [{
    band: "<0d",
    count: 6,
    tone: "fail"
  }, {
    band: "0–5d",
    count: 18,
    tone: "warn"
  }, {
    band: "6–20d",
    count: 34,
    tone: "pass"
  }, {
    band: "21–40d",
    count: 21,
    tone: "pass"
  }, {
    band: ">40d",
    count: 12,
    tone: "info"
  }],
  activities: [{
    id: "A1010",
    name: "Foundation pour",
    s: 0,
    d: 3,
    crit: true,
    tf: 0,
    baseline: {
      s: 0,
      d: 3
    }
  }, {
    id: "A1020",
    name: "Steel erection",
    s: 3,
    d: 4,
    crit: true,
    tf: 0,
    baseline: {
      s: 3,
      d: 3
    }
  }, {
    id: "A1030",
    name: "MEP rough-in",
    s: 5,
    d: 5,
    crit: false,
    tf: 4,
    baseline: {
      s: 5,
      d: 5
    }
  }, {
    id: "A1040",
    name: "Building envelope",
    s: 7,
    d: 4,
    crit: true,
    tf: 0,
    baseline: {
      s: 6,
      d: 4
    }
  }, {
    id: "A1050",
    name: "Interior fit-out",
    s: 9,
    d: 6,
    crit: false,
    tf: 2,
    baseline: {
      s: 9,
      d: 5
    }
  }, {
    id: "A1060",
    name: "Commissioning",
    s: 13,
    d: 3,
    crit: true,
    tf: 0,
    baseline: {
      s: 11,
      d: 3
    }
  }, {
    id: "A1070",
    name: "Punch list",
    s: 15,
    d: 2,
    crit: false,
    tf: 6,
    baseline: {
      s: 14,
      d: 2
    }
  }, {
    id: "A1080",
    name: "Turnover",
    s: 16,
    d: 2,
    crit: true,
    tf: 0,
    baseline: {
      s: 14,
      d: 2
    }
  }],
  risks: [{
    id: "R-014",
    name: "Envelope subcontractor capacity",
    p: "60%",
    impact: "12d",
    exposure: "7.2d",
    owner: "PM",
    tone: "fail"
  }, {
    id: "R-021",
    name: "Long-lead switchgear delivery",
    p: "45%",
    impact: "10d",
    exposure: "4.5d",
    owner: "Procurement",
    tone: "fail"
  }, {
    id: "R-008",
    name: "Commissioning agent availability",
    p: "35%",
    impact: "8d",
    exposure: "2.8d",
    owner: "Scheduler",
    tone: "warn"
  }, {
    id: "R-030",
    name: "Permit renewal cycle",
    p: "25%",
    impact: "6d",
    exposure: "1.5d",
    owner: "Legal",
    tone: "warn"
  }, {
    id: "R-017",
    name: "Weather window — crane lifts",
    p: "20%",
    impact: "4d",
    exposure: "0.8d",
    owner: "Site",
    tone: "pass"
  }],
  mc: {
    bins: ["Sep 08", "Sep 15", "Sep 22", "Sep 29", "Oct 06", "Oct 13", "Oct 20"],
    counts: [3, 9, 18, 26, 22, 14, 8],
    p50: "Sep 29",
    p80: "Oct 13",
    deterministic: "Sep 22"
  },
  audit: [{
    time: "14:02:11",
    event: "Export — Falcon forensic ledger.pdf",
    dest: "Local disk",
    egress: "NONE"
  }, {
    time: "13:47:52",
    event: "Export — Portfolio health.xlsx",
    dest: "Local disk",
    egress: "NONE"
  }, {
    time: "11:20:08",
    event: "Outbound network probe (telemetry)",
    dest: "0.0.0.0",
    egress: "BLOCKED"
  }, {
    time: "09:14:33",
    event: "SRA template round-trip (upload)",
    dest: "Local ingest",
    egress: "NONE"
  }, {
    time: "08:00:01",
    event: "Session start — model weights local",
    dest: "—",
    egress: "NONE"
  }],
  facts: [{
    id: "FACT-2291",
    label: "Schedule Performance Index (SPI)",
    value: "0.92",
    confirmed: false,
    formula: "SPI = EV / PV = 78.0 / 84.8",
    source: "Update #42 · data date 2026-07-13",
    standard: "EVM · ANSI/EIA-748",
    caveat: "Earning-rule may not match this schedule's %-complete method — treat as directional until reconciled.",
    narrative: "Falcon is behind schedule: 92 cents of planned work earned for every dollar planned. The gap widened 0.06 this update, driven by the Building envelope slip."
  }, {
    id: "FACT-2292",
    label: "Cost Performance Index (CPI)",
    value: "1.04",
    confirmed: true,
    formula: "CPI = EV / AC = 78.0 / 75.0",
    source: "Update #42 · data date 2026-07-13",
    standard: "EVM · ANSI/EIA-748",
    narrative: "Falcon is under cost: $1.04 of value earned per dollar spent. Cost efficiency is holding while schedule erodes — a classic trade of float for burn rate."
  }, {
    id: "FACT-3117",
    label: "Total float — Building envelope",
    value: "-4d",
    confirmed: true,
    formula: "TF = LF − EF = 2026-09-02 − 2026-09-06",
    source: "CPM run · Update #42",
    standard: "Driving-path forward/backward pass",
    narrative: "The Building envelope activity is 4 workdays behind its late finish — it is now driving the critical path into Commissioning."
  }, {
    id: "FACT-4420",
    label: "DCMA-14 · Hard constraints",
    value: "3 breaches",
    confirmed: true,
    formula: "count(constraint ∈ {MSO, MFO, hard SNET})",
    source: "Update #42",
    standard: "NASA Acumen .aft · DCMA-14 check 5",
    narrative: "Three activities carry hard constraints that override network logic, masking true float. Removing them is the fastest way to restore a defensible critical path."
  }],
  quality: {
    healthScore: 71,
    constraints: [{
      type: "Must-Start-On (hard)",
      n: 1,
      kind: "fail"
    }, {
      type: "Must-Finish-On (hard)",
      n: 1,
      kind: "fail"
    }, {
      type: "Hard SNET",
      n: 1,
      kind: "fail"
    }, {
      type: "Soft SNET",
      n: 9,
      kind: "warn"
    }, {
      type: "Finish-No-Later-Than",
      n: 2,
      kind: "warn"
    }, {
      type: "As-Late-As-Possible",
      n: 1,
      kind: "warn"
    }],
    resources: {
      labor: [96, 112, 128, 134, 126, 108],
      capacity: 130
    },
    density: [14, 22, 31, 38, 34, 26]
  },
  milestones: {
    names: ["Design freeze", "IOT&E start", "Turnover"],
    slip: [[0, 1, 2, 4, 5, 8, 11], [0, 0, 1, 2, 2, 3, 5], [0, 1, 3, 5, 7, 9, 14]]
  },
  evmFull: {
    sv: -6.8,
    cv: 3.0,
    eac: 155,
    etc: 80,
    vac: -5,
    bac: 150,
    tcpi: 1.08,
    spit: 0.9,
    bei: 0.94,
    cpli: 0.97
  },
  forensics: {
    score: 62,
    klass: "ELEVATED",
    patterns: [{
      name: "Logic changes",
      detail: "+9 added · 4 removed · 6 modified",
      status: "warn"
    }, {
      name: "Constraint changes",
      detail: "2 hard constraints added on the driving path",
      status: "fail"
    }, {
      name: "Duration gaming",
      detail: "3 ODs cut >30% with no scope note",
      status: "fail"
    }, {
      name: "Out-of-sequence progress",
      detail: "12 activities progressed against logic",
      status: "warn"
    }, {
      name: "Phantom activities",
      detail: "1 added then removed, #40→#42",
      status: "warn"
    }, {
      name: "Float manipulation",
      detail: "No artificial float insertion detected",
      status: "pass"
    }],
    windows: [{
      win: "#36→37",
      d: 1,
      resp: "Contractor"
    }, {
      win: "#37→38",
      d: 3,
      resp: "Contractor"
    }, {
      win: "#38→39",
      d: 4,
      resp: "Owner"
    }, {
      win: "#39→40",
      d: 2,
      resp: "Force majeure"
    }, {
      win: "#40→41",
      d: 2,
      resp: "Concurrent"
    }, {
      win: "#41→42",
      d: 5,
      resp: "Contractor"
    }],
    respColors: {
      "Owner": "var(--status-info)",
      "Contractor": "var(--status-fail)",
      "Concurrent": "var(--viz-4)",
      "Force majeure": "var(--status-neutral)"
    },
    matrix: [["Owner", 4, "info"], ["Contractor", 9, "fail"], ["Concurrent", 2, "warn"], ["Force majeure", 2, "neutral"]],
    cpShift: [{
      upd: "#38",
      text: "Driving path shifted: MEP rough-in → Building envelope (hard constraint added)"
    }, {
      upd: "#40",
      text: "Near-critical path within 2d of driving: Interior fit-out chain"
    }, {
      upd: "#42",
      text: "Commissioning and Turnover joined the driving path (envelope slip)"
    }]
  },
  drivingLinks: [{
    type: "FS",
    lag: 0
  }, {
    type: "FS",
    lag: 0
  }, {
    type: "FS",
    lag: 2
  }, {
    type: "FS",
    lag: 0
  }],
  rels: [{
    pred: "A1010",
    succ: "A1020",
    type: "FS",
    lag: 0,
    driving: "Yes"
  }, {
    pred: "A1020",
    succ: "A1030",
    type: "SS",
    lag: 2,
    driving: "—"
  }, {
    pred: "A1020",
    succ: "A1040",
    type: "FS",
    lag: 0,
    driving: "Yes"
  }, {
    pred: "A1030",
    succ: "A1050",
    type: "SS",
    lag: 4,
    driving: "—"
  }, {
    pred: "A1040",
    succ: "A1060",
    type: "FS",
    lag: 2,
    driving: "Yes"
  }, {
    pred: "A1050",
    succ: "A1070",
    type: "FS",
    lag: 0,
    driving: "—"
  }, {
    pred: "A1060",
    succ: "A1080",
    type: "FS",
    lag: 0,
    driving: "Yes"
  }, {
    pred: "A1070",
    succ: "A1080",
    type: "FS",
    lag: 0,
    driving: "—"
  }],
  ingest: {
    formats: [{
      ext: "XER",
      app: "Primavera P6"
    }, {
      ext: "XML",
      app: "P6 / MSP XML"
    }, {
      ext: "MPP",
      app: "Microsoft Project"
    }, {
      ext: "XLSX",
      app: "P6/MSP export · SRA template"
    }, {
      ext: "CSV",
      app: "Generic activity table"
    }, {
      ext: "JSON",
      app: "AISMAT interchange"
    }],
    pipeline: [{
      step: "Parse",
      desc: "falcon_2026-07-13.xer · 366 activities, 981 relationships, 3 calendars",
      status: "pass"
    }, {
      step: "Validate",
      desc: "2 rejections quarantined with specific reasons — nothing half-loaded",
      status: "warn"
    }, {
      step: "CPM run",
      desc: "Forward/backward pass complete · driving path: 5 activities",
      status: "pass"
    }, {
      step: "Fact ledger",
      desc: "1,214 facts written · AI narratives grounded to fact IDs, disclosed",
      status: "pass"
    }],
    rejections: [{
      row: "Activity A2140",
      reason: "Circular relationship A2140 → A2150 → A2140 — break the loop and re-import."
    }, {
      row: "Calendar CAL-7",
      reason: "Workweek undefined (0 workdays) — assign hours or map to CAL-1."
    }],
    history: [{
      upd: "#42",
      file: "falcon_2026-07-13.xer",
      fmt: "XER",
      acts: 366,
      delta: "-7d float",
      when: "2026-07-13"
    }, {
      upd: "#41",
      file: "falcon_2026-06-15.xer",
      fmt: "XER",
      acts: 362,
      delta: "-2d float",
      when: "2026-06-15"
    }, {
      upd: "#40",
      file: "falcon_2026-05-18.mpp",
      fmt: "MPP",
      acts: 360,
      delta: "-2d float",
      when: "2026-05-18"
    }, {
      upd: "#39",
      file: "falcon_2026-04-13.xer",
      fmt: "XER",
      acts: 355,
      delta: "-4d float",
      when: "2026-04-13"
    }]
  }
};
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/aismat/data.js", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.StatusChip = __ds_scope.StatusChip;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.CaveatBanner = __ds_scope.CaveatBanner;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.CitationChip = __ds_scope.CitationChip;

__ds_ns.DcmaStrip = __ds_scope.DcmaStrip;

__ds_ns.GanttChart = __ds_scope.GanttChart;

__ds_ns.InstrumentPanel = __ds_scope.InstrumentPanel;

__ds_ns.MetricTile = __ds_scope.MetricTile;

__ds_ns.ProgramTile = __ds_scope.ProgramTile;

__ds_ns.Sparkline = __ds_scope.Sparkline;

__ds_ns.TrendChart = __ds_scope.TrendChart;

__ds_ns.AirGapIndicator = __ds_scope.AirGapIndicator;

__ds_ns.RoleStrip = __ds_scope.RoleStrip;

__ds_ns.Tabs = __ds_scope.Tabs;

})();
