from __future__ import annotations

from pathlib import Path
from typing import Any

from forge.domain import GeneratedFile, ProjectSpec, Question, QuestionType
from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)

_SRC_APP_TSX = """\
import { useState } from "react"

function App() {
  const [count, setCount] = useState(0)

  return (
    <div>
      <h1>Vite + React</h1>
      <div>
        <button onClick={() => setCount((c) => c + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
    </div>
  )
}

export default App
"""

_SRC_APP_JSX = """\
import { useState } from "react"

function App() {
  const [count, setCount] = useState(0)

  return (
    <div>
      <h1>Vite + React</h1>
      <div>
        <button onClick={() => setCount((c) => c + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.jsx</code> and save to test HMR
        </p>
      </div>
    </div>
  )
}

export default App
"""

_SRC_MAIN = """\
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
"""


_INDEX_HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.{ext}"></script>
  </body>
</html>
"""


def _build_index_html(ext: str) -> str:
    return _INDEX_HTML_TEMPLATE.replace("{ext}", ext)


_SRC_INDEX_CSS = """\
:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;
  color-scheme: light dark;
  color: #213547;
  background-color: #ffffff;
}

body {
  margin: 0;
  display: flex;
  place-items: center;
  min-width: 320px;
  min-height: 100vh;
}

h1 {
  font-size: 3.2em;
  line-height: 1.1;
}

button {
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  font-family: inherit;
  background-color: #f9f9f9;
  cursor: pointer;
  transition: border-color 0.25s;
}

button:hover {
  border-color: #646cff;
}
"""

_VITE_CONFIG_TS = """\
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
})
"""

_WEBPACK_CONFIG_TEMPLATE = """\
const path = require("path")
const HtmlWebpackPlugin = require("html-webpack-plugin")

module.exports = {
  entry: "./src/main.{ext}",
  output: {
    path: path.resolve(__dirname, "dist"),
    filename: "bundle.js",
  },
  resolve: {
    extensions: [".ts", ".tsx", ".js", ".jsx"],
  },
  module: {
    rules: [
      {
        test: /\\.[jt]sx?$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
          options: {
            presets: [
              "@babel/preset-env",
              "@babel/preset-react",
              "@babel/preset-typescript",
            ],
          },
        },
      },
      {
        test: /\\.css$/,
        use: ["style-loader", "css-loader", "postcss-loader"],
      },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: "./public/index.html",
    }),
  ],
  devServer: {
    port: 3000,
    hot: true,
  },
}
"""


def _build_webpack_config(ext: str) -> str:
    return _WEBPACK_CONFIG_TEMPLATE.replace("{ext}", ext)


_TS_CONFIG_JSON = """\
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
"""

_SRC_VITE_ENV_D_TS = """\
/// <reference types="vite/client" />
"""

_POSTCSS_CONFIG_JS = """\
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""


def _build_tailwind_config(include_typescript: bool) -> str:
    content_glob = "{ts,tsx}" if include_typescript else "{js,jsx}"
    return f"""\
/** @type {{import('tailwindcss').Config}} */
export default {{
  content: [
    "./index.html",
    "./src/**/*.{content_glob}",
  ],
  theme: {{
    extend: {{}},
  }},
  plugins: [],
}}
"""


class ReactPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "react"
    display_name = "React"
    description = "React frontend with Vite + TypeScript"
    requires: list[str] = []

    @staticmethod
    def _config(spec: ProjectSpec) -> dict[str, Any]:
        return spec.config.get("react", {})

    def questions(self) -> list[Question]:
        return [
            Question(
                key="bundler",
                label="Bundler",
                question_type=QuestionType.CHOICE,
                required=True,
                default="vite",
                description="Bundler to use for the React project",
                options=["vite", "webpack"],
            ),
            Question(
                key="include_typescript",
                label="Include TypeScript",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=True,
                description="Include TypeScript support",
            ),
            Question(
                key="include_router",
                label="Include React Router",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=False,
                description="Include React Router for client-side routing",
            ),
            Question(
                key="include_tailwind",
                label="Include Tailwind CSS",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=False,
                description="Include Tailwind CSS for styling",
            ),
            Question(
                key="state_management",
                label="State Management",
                question_type=QuestionType.CHOICE,
                required=True,
                default="none",
                description="State management library",
                options=["none", "zustand", "redux"],
            ),
        ]

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        config = self._config(spec)
        bundler = config.get("bundler", "vite")
        include_ts = config.get("include_typescript", True)
        include_tailwind = config.get("include_tailwind", False)

        ext = "tsx" if include_ts else "jsx"

        files = [
            GeneratedFile(
                path=Path(f"src/App.{ext}"),
                content=_SRC_APP_TSX if include_ts else _SRC_APP_JSX,
            ),
            GeneratedFile(
                path=Path(f"src/main.{ext}"),
                content=_SRC_MAIN,
            ),
            GeneratedFile(path=Path("public/index.html"), content=_build_index_html(ext)),
            GeneratedFile(path=Path("src/index.css"), content=_SRC_INDEX_CSS),
        ]

        if bundler == "vite":
            files.append(GeneratedFile(path=Path("vite.config.ts"), content=_VITE_CONFIG_TS))
        else:
            files.append(
                GeneratedFile(
                    path=Path("webpack.config.js"),
                    content=_build_webpack_config(ext),
                )
            )

        if include_ts:
            files.append(GeneratedFile(path=Path("tsconfig.json"), content=_TS_CONFIG_JSON))
            if bundler == "vite":
                files.append(
                    GeneratedFile(
                        path=Path("src/vite-env.d.ts"),
                        content=_SRC_VITE_ENV_D_TS,
                    )
                )

        if include_tailwind:
            files.append(
                GeneratedFile(
                    path=Path("tailwind.config.js"),
                    content=_build_tailwind_config(include_ts),
                )
            )
            files.append(GeneratedFile(path=Path("postcss.config.js"), content=_POSTCSS_CONFIG_JS))

        return files

    def directories(self, spec: ProjectSpec) -> list[str]:
        return ["src/", "src/components/", "src/pages/", "public/"]

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        config = self._config(spec)
        include_ts = config.get("include_typescript", True)

        deps: list[str] = ["react", "react-dom"]

        if include_ts:
            deps.append("typescript")
            deps.append("@types/react")
            deps.append("@types/react-dom")

        if config.get("include_router", False):
            deps.append("react-router-dom")

        if config.get("include_tailwind", False):
            deps.append("tailwindcss")
            deps.append("postcss")
            deps.append("autoprefixer")

        sm = config.get("state_management", "none")
        if sm == "zustand":
            deps.append("zustand")
        elif sm == "redux":
            deps.append("@reduxjs/toolkit")
            deps.append("react-redux")

        return deps

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: Any) -> None:
        config = self._config(spec)
        bundler = config.get("bundler", "vite")
        if bundler != "vite":
            return

        include_ts = config.get("include_typescript", True)
        template = "react-ts" if include_ts else "react"

        executor.run(
            ["npm", "create", "vite", ".", "--", "--template", template],
            cwd=target_dir,
        )

        install: list[str] = ["npm", "install"]

        if config.get("include_router", False):
            install.append("react-router-dom")

        if config.get("include_tailwind", False):
            install.append("tailwindcss")
            install.append("postcss")
            install.append("autoprefixer")

        sm = config.get("state_management", "none")
        if sm == "zustand":
            install.append("zustand")
        elif sm == "redux":
            install.append("@reduxjs/toolkit")
            install.append("react-redux")

        if len(install) > 2:
            executor.run(install, cwd=target_dir)
