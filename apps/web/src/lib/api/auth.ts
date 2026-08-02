import { apiRequest } from "@/lib/api/client";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/v1/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/v1/auth/me", {
    method: "GET",
    token,
  });
}

export async function logoutRequest(token: string): Promise<undefined> {
  return apiRequest<undefined>("/v1/auth/logout", {
    method: "POST",
    token,
  });
}
