# Imagen de desarrollo de las interfaces: uis/website (puerto 3000) y uis/backoffice (puerto 3001),
# las dos con `next dev` y recarga en caliente, lanzadas por start.sh.
#
# Se construye desde docker-compose.yml (raíz) con:
#   context: ./uis
#   additional_contexts: brasa-core: ./packages/brasa-core
# El backoffice depende de file:../../packages/brasa-core, fuera de ./uis, así que el paquete llega por
# el contexto adicional `brasa-core`. La imagen reproduce la estructura del monorepo (/repo/...) para que
# esa ruta, y la raíz de Turbopack del backoffice (../..), sigan siendo válidas dentro del contenedor.

FROM node:22-alpine

ENV NEXT_TELEMETRY_DISABLED=1

# Usuario sin privilegios `node` (uid 1000, incluido en la imagen oficial), dueño de /repo.
RUN mkdir -p /repo/uis && chown -R node:node /repo
USER node
WORKDIR /repo/uis

# 1. Paquete local @repo/brasa-core (TypeScript sin compilar; el backoffice lo transpila).
COPY --chown=node:node --from=brasa-core package.json index.ts /repo/packages/brasa-core/
COPY --chown=node:node --from=brasa-core types /repo/packages/brasa-core/types
COPY --chown=node:node --from=brasa-core utils /repo/packages/brasa-core/utils

# 2. Dependencias de cada aplicación, en capas propias: solo se reinstalan si cambia su lockfile.
#    npm ci instala los binarios nativos de Linux musl (SWC, lightningcss, Tailwind) que traen los lockfiles.
COPY --chown=node:node website/package.json website/package-lock.json website/
RUN cd website && npm ci --no-audit --no-fund

COPY --chown=node:node backoffice/package.json backoffice/package-lock.json backoffice/
RUN cd backoffice && npm ci --no-audit --no-fund

# 3. Código de las dos aplicaciones y start.sh. En desarrollo, el bind mount de docker-compose.yml lo
#    sustituye por el del host; node_modules y .next se quedan en volúmenes del contenedor.
COPY --chown=node:node . .
RUN mkdir -p website/.next backoffice/.next

EXPOSE 3000 3001

CMD ["sh", "./start.sh"]
