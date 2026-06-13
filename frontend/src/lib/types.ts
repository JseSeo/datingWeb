export type UserStatus = "pending" | "active" | "suspended";

export interface UserOut {
  id: number;
  email: string;
  name: string;
  university: string;
  status: UserStatus;
  profile_photo: string | null;
  bio: string | null;
  instagram: string | null;
  kakao_id: string | null;
  phone: string | null;
  matching_paused: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  university: string;
}
