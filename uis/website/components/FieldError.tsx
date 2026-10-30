export default function FieldError({ id, message }: { id: string; message?: string }) {
  return (
    <p id={id} aria-live="polite" className={message ? "mt-1 text-sm text-red-600" : "hidden"}>
      {message}
    </p>
  );
}
