import { env } from "../lib/env";

type OIDCDiscoveryDocument = {
  authorization_endpoint: string;
  token_endpoint: string;
};

type OIDCTransaction = {
  codeVerifier: string;
  redirectUri: string;
  state: string;
};

const DISCOVERY_CACHE_KEY = "ganttbuddy.frontend.oidc.discovery";
const TRANSACTION_STORAGE_KEY = "ganttbuddy.frontend.oidc.transaction";

function assertOidcConfigured() {
  if (!env.oidcAuthority || !env.oidcClientId) {
    throw new Error("OIDC is not configured. Set VITE_OIDC_AUTHORITY and VITE_OIDC_CLIENT_ID.");
  }
}

function readTransaction(): OIDCTransaction | null {
  const raw = window.sessionStorage.getItem(TRANSACTION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as OIDCTransaction;
  } catch {
    window.sessionStorage.removeItem(TRANSACTION_STORAGE_KEY);
    return null;
  }
}

function writeTransaction(transaction: OIDCTransaction) {
  window.sessionStorage.setItem(TRANSACTION_STORAGE_KEY, JSON.stringify(transaction));
}

export function clearOidcTransaction() {
  window.sessionStorage.removeItem(TRANSACTION_STORAGE_KEY);
}

async function sha256Base64Url(value: string) {
  const encoder = new TextEncoder();
  const hash = await window.crypto.subtle.digest("SHA-256", encoder.encode(value));
  return base64UrlEncode(hash);
}

function base64UrlEncode(value: ArrayBuffer) {
  const bytes = new Uint8Array(value);
  let stringValue = "";
  bytes.forEach((byte) => {
    stringValue += String.fromCharCode(byte);
  });
  return btoa(stringValue).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function randomString(length = 64) {
  const bytes = new Uint8Array(length);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function fetchDiscoveryDocument(): Promise<OIDCDiscoveryDocument> {
  assertOidcConfigured();
  const cached = window.sessionStorage.getItem(DISCOVERY_CACHE_KEY);
  if (cached) {
    try {
      return JSON.parse(cached) as OIDCDiscoveryDocument;
    } catch {
      window.sessionStorage.removeItem(DISCOVERY_CACHE_KEY);
    }
  }

  const metadataUrl = new URL(".well-known/openid-configuration", `${env.oidcAuthority.replace(/\/+$/, "")}/`);
  const response = await fetch(metadataUrl.toString());
  if (!response.ok) {
    throw new Error(`Failed to load OIDC metadata (${response.status})`);
  }

  const discovery = (await response.json()) as OIDCDiscoveryDocument;
  window.sessionStorage.setItem(DISCOVERY_CACHE_KEY, JSON.stringify(discovery));
  return discovery;
}

export async function beginOidcLogin() {
  const discovery = await fetchDiscoveryDocument();
  const state = randomString(16);
  const codeVerifier = randomString(48);
  const codeChallenge = await sha256Base64Url(codeVerifier);

  writeTransaction({
    codeVerifier,
    redirectUri: env.oidcRedirectUri,
    state,
  });

  const authorizationUrl = new URL(discovery.authorization_endpoint);
  authorizationUrl.searchParams.set("client_id", env.oidcClientId);
  authorizationUrl.searchParams.set("redirect_uri", env.oidcRedirectUri);
  authorizationUrl.searchParams.set("response_type", "code");
  authorizationUrl.searchParams.set("scope", env.oidcScope);
  authorizationUrl.searchParams.set("code_challenge", codeChallenge);
  authorizationUrl.searchParams.set("code_challenge_method", "S256");
  authorizationUrl.searchParams.set("state", state);

  window.location.assign(authorizationUrl.toString());
}

export async function completeOidcLoginFromCallback(params: URLSearchParams) {
  assertOidcConfigured();
  const error = params.get("error");
  if (error) {
    throw new Error(params.get("error_description") || error);
  }

  const code = params.get("code");
  const state = params.get("state");
  if (!code || !state) {
    throw new Error("Missing authorization response parameters.");
  }

  const transaction = readTransaction();
  if (!transaction || transaction.state !== state) {
    throw new Error("OIDC login state did not match the initiated request.");
  }

  const discovery = await fetchDiscoveryDocument();
  const body = new URLSearchParams();
  body.set("grant_type", "authorization_code");
  body.set("client_id", env.oidcClientId);
  body.set("code", code);
  body.set("redirect_uri", transaction.redirectUri);
  body.set("code_verifier", transaction.codeVerifier);

  const tokenResponse = await fetch(discovery.token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!tokenResponse.ok) {
    let message = `OIDC token exchange failed (${tokenResponse.status})`;
    try {
      const payload = await tokenResponse.json();
      message = payload.error_description ?? payload.error ?? message;
    } catch {
      const text = await tokenResponse.text();
      if (text) {
        message = text;
      }
    }
    throw new Error(message);
  }

  const payload = (await tokenResponse.json()) as { id_token?: string };
  if (!payload.id_token) {
    throw new Error("OIDC provider did not return an id_token.");
  }

  return payload.id_token;
}
