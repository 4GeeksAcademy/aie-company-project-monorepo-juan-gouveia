type ButtonVariant = "primary" | "secondary" | "danger";
type ButtonSize = "sm" | "md";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const BASE =
  "rounded-md py-2 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:cursor-not-allowed";

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary:
    "bg-red-700 text-white hover:bg-red-800 focus-visible:ring-offset-2 disabled:opacity-50",
  secondary:
    "border border-red-200 text-red-700 hover:bg-red-50 disabled:border-gray-200 disabled:text-gray-400 disabled:hover:bg-transparent",
  danger: "border border-red-700 text-red-700 hover:bg-red-50 disabled:opacity-60",
};

const SIZE_CLASS: Record<ButtonSize, string> = { sm: "px-3", md: "px-4" };

export default function Button({
  variant = "primary",
  size = "sm",
  type = "button",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${BASE} ${VARIANT_CLASS[variant]} ${SIZE_CLASS[size]} ${className}`.trim()}
      {...props}
    />
  );
}
