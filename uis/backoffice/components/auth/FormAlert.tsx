interface FormAlertProps {
  children: React.ReactNode;
  // "error" para fallos; "info" para avisos como "tu sesión ha caducado"; "success" para confirmaciones.
  tone?: "error" | "info" | "success";
}

const TONE_CLASS: Record<NonNullable<FormAlertProps["tone"]>, string> = {
  error: "border-red-200 bg-red-50 text-red-700",
  info: "border-amber-200 bg-amber-50 text-amber-900",
  success: "border-green-200 bg-green-50 text-green-800",
};

export default function FormAlert({ children, tone = "error" }: FormAlertProps) {
  const toneClass = TONE_CLASS[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-md border p-3 text-sm ${toneClass}`}>
      {children}
    </div>
  );
}
