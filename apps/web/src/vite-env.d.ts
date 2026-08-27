/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_UKB_API_BASE_URL?: string;
  readonly VITE_UKB_API_TOKEN?: string;
  readonly VITE_COPILOTKIT_RUNTIME_URL?: string;
  readonly VITE_COPILOTKIT_RUNTIME_TOKEN?: string;
  readonly VITE_COPILOTKIT_AGENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
