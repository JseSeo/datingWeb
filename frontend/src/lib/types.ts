export type UserStatus = "pending" | "active" | "suspended" | "withdrawn";

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

export interface OjakgyoCreate {
  person_a_name: string;
  person_a_university: string;
  person_b_name: string;
  person_b_university: string;
}

export interface OjakgyoOut extends OjakgyoCreate {
  id: number;
  recommender_id: number;
  created_at: string;
}

export interface RedThreadTarget {
  target_name: string;
  target_university: string;
}

export interface RedThreadOut {
  targets: RedThreadTarget[];
}

export interface RedThreadReceived {
  count: number;
}
