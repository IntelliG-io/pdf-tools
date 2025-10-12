# Frontend

This package contains the user interface for the PDF tools project. It is a Vite + React application styled with Tailwind CSS and shadcn/ui components. The app currently works with mock service implementations located in `src/services`, so it can be run locally without any backend services.

## Getting started

1. Install dependencies (requires Node.js 18 or later):
   ```sh
   npm install
   ```
2. Start the development server:
   ```sh
   npm run dev
   ```
   The app will be served at [http://localhost:5173](http://localhost:5173).
3. Create a production build:
   ```sh
   npm run build
   ```
   The compiled assets will be output to the `dist/` directory.

## Available scripts

| Command         | Description                         |
| --------------- | ----------------------------------- |
| `npm run dev`   | Start the Vite development server.  |
| `npm run build` | Build the production bundle.        |
| `npm run lint`  | Run ESLint on the project files.    |
| `npm run preview` | Preview the production build locally. |

## Project structure

- `src/` – React components, routes, hooks, and mock service implementations.
- `public/` – Static assets copied as-is during the build.
- `tailwind.config.ts` – Tailwind CSS configuration.
- `vite.config.ts` – Vite configuration.

All UI work should happen inside the `src/` directory.
