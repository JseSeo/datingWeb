export type UserStatus = "pending" | "active" | "suspended" | "withdrawn";

export interface UserOut {
  id: number;
  email: string;
  name: string;
  university: string;
  gender: "male" | "female";
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
  gender: "male" | "female";
  agreed_terms: boolean;
  agreed_privacy: boolean;
  agreed_age_14: boolean;
  instagram?: string | null;
  kakao_id?: string | null;
  phone?: string | null;
  admission_year?: number | null;
}

export interface OjakgyoCreate {
  person_a_name: string;
  person_a_university: string;
  person_b_name: string;
  person_b_university: string;
  person_a_admission_year?: number | null;
  person_b_admission_year?: number | null;
}

export interface OjakgyoOut extends OjakgyoCreate {
  id: number;
  recommender_id: number;
  created_at: string;
}

export interface RedThreadTarget {
  target_name: string;
  target_university: string;
  target_admission_year?: number | null;
}

export interface RedThreadOut {
  targets: RedThreadTarget[];
}

export interface RedThreadReceived {
  count: number;
}

export type VerificationStatus = "pending" | "approved" | "rejected";

export interface VerificationOut {
  id: number;
  user_id: number;
  status: VerificationStatus;
  reviewed_at: string | null;
  created_at: string;
}

export interface AdminVerificationOut {
  id: number;
  user_id: number;
  status: VerificationStatus;
  reviewed_at: string | null;
  created_at: string;
  name: string;
  university: string;
}

export interface SurveyData {
  responses: Record<string, unknown>;
  absolute: string[];
}

export interface SurveyOut {
  answers: SurveyData | Record<string, never>;
  updated_at: string | null;
}

export type ReportType = "report" | "suggestion";

export interface ReportPayload {
  type: ReportType;
  target_name: string | null;
  target_university: string | null;
  reason: string;
}

export interface ReportOut {
  id: number;
  type: ReportType;
  target_name: string | null;
  target_university: string | null;
  reason: string;
  created_at: string;
}

export interface AdminReportOut {
  id: number;
  type: ReportType;
  target_name: string | null;
  target_university: string | null;
  reason: string;
  created_at: string;
  handled: boolean;
  reporter_name: string;
  reporter_university: string;
}

export interface MatchRoundOut {
  id: number;
  scheduled_at: string;
}

export interface AdminMatchRoundOut {
  id: number;
  scheduled_at: string;
  status: "pending" | "running" | "done";
  /** 마지막 자동 실행 실패·놓침 사유. 성공하면 null로 돌아온다 */
  last_error: string | null;
}

export interface MatchingRunOut {
  matched: number;
  unmatched: number;
  guaranteed: number;
}

export interface UniversityWeightOut {
  id: number;
  university_a: string;
  university_b: string;
  bonus: number;
  active: boolean;
  note: string | null;
}

/** 생성·수정 공용 본문. university_b가 빈 문자열이면 단일 대학 규칙. */
export interface UniversityWeightIn {
  university_a: string;
  university_b: string;
  bonus: number;
  active: boolean;
  note: string | null;
}

export interface UniversityOut {
  id: number;
  name: string;
  active: boolean;
}

export interface MatchResultOut {
  name: string;
  university: string;
  instagram: string | null;
  kakao_id: string | null;
  phone: string | null;
  executed_at: string;
}

export type Section = "self" | "partner";

export type QuestionType =
  | "single"
  | "multi"
  | "scale"
  | "number"
  | "ranking"
  | "image-single"
  | "image-multi";

export interface Choice {
  id: string;
  label: string;
}

export interface FaceChoice {
  id: string;
  label: string;
  image: string;
}

export interface Question {
  id: string;
  section: Section;
  label: string;
  type: QuestionType;
  choices?: Choice[] | null;
  face?: boolean;
  min?: number | null;
  max?: number | null;
  rank_items?: Choice[] | null;
  scale_labels?: [string, string] | null;
  unit?: string | null;
  male_only?: boolean;
  no_pref_id?: string | null;
}

export interface SurveyCatalog {
  questions: Question[];
  face_types: FaceChoice[];
  face_any_id: string;
}
