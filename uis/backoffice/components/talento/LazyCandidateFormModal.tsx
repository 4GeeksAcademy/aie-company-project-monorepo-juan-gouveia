"use client";

import dynamic from "next/dynamic";

// Carga diferida del formulario de candidato: solo aparece al pulsar "Añadir candidato" (/talento) o
// "Editar" (/talento/candidates/[id]), así que no forma parte de lo que se descarga al abrir esas
// vistas. Las dos páginas importan este módulo para declarar la carga en un solo sitio.
const CandidateFormModal = dynamic(() => import("@/components/talento/CandidateFormModal"));

export default CandidateFormModal;
