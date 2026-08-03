# Frontend — Panel administrativo

Next.js (App Router) + TypeScript estricto + Tailwind CSS.

Consume exclusivamente la API REST del Core (`NEXT_PUBLIC_API_URL`). Sin lógica de negocio ni acceso a base de datos.

## Desarrollo local

```bash
npm install
cp .env.example .env.local
npm run dev
```

## Calidad

```bash
npm run lint
npm run typecheck
npm run build
```
