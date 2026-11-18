import Button from "@/components/Button";

interface ShowMoreButtonProps {
  visible: number;
  total: number;
  nextCount: number;
  onShowMore: () => void;
}

// Pie de las listas que se pintan por partes (useShowMore): cuántas filas se ven y el botón para
// añadir las siguientes. El recuento se anuncia a los lectores de pantalla al cambiar, y el foco se
// queda en el botón, así que se puede seguir pulsando sin volver a buscarlo.
export default function ShowMoreButton({ visible, total, nextCount, onShowMore }: ShowMoreButtonProps) {
  return (
    <div className="flex flex-col items-center gap-2 sm:flex-row sm:justify-between">
      <p className="text-sm text-gray-700" aria-live="polite">
        Mostrando {visible} de {total}.
      </p>
      {nextCount > 0 && (
        <Button variant="secondary" size="md" onClick={onShowMore}>
          Mostrar {nextCount} más
        </Button>
      )}
    </div>
  );
}
