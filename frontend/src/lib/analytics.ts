import posthog from "posthog-js";

// Baked in at build time. Without a token, analytics and session replay stay off.
const TOKEN = process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN;
// Path on our own domain that Caddy forwards to PostHog, so ad blockers don't drop events
const API_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "/k7r";
const UI_HOST = process.env.NEXT_PUBLIC_POSTHOG_UI_HOST || "https://us.posthog.com";

let started = false;

export function initAnalytics(): void {
  if (started || !TOKEN || typeof window === "undefined") return;
  started = true;
  posthog.init(TOKEN, {
    api_host: API_HOST,
    ui_host: UI_HOST,
    defaults: "2026-05-30",
    person_profiles: "identified_only",
    session_recording: {
      // Inputs stay masked (the login form has the email and the one-time code);
      // sent chat messages are visible. Elements with the "ph-mask" class (emails) are masked.
      maskAllInputs: true,
    },
  });
}

/** Same id as the backend (SHA-256 of the email), so replays line up with LLM traces. */
async function distinctId(email: string): Promise<string> {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(email));
  return Array.from(new Uint8Array(bytes), (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function identifyUser(email: string): Promise<void> {
  if (!started) return;
  try {
    posthog.identify(await distinctId(email));
  } catch {
    // crypto.subtle needs a secure context; skip identification without it
  }
}

export function resetAnalytics(): void {
  if (started) posthog.reset();
}
