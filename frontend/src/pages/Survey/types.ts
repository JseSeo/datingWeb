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
  image: string; // 에셋경로 (placeholder, 운영 전 교체)
}

export interface Question {
  id: string;
  section: Section;
  label: string;
  type: QuestionType;
  choices?: Choice[];          // single | multi
  face?: boolean;              // image-single | image-multi → FACE_TYPES 사용
  rankItems?: Choice[];        // ranking
  scaleLabels?: [string, string]; // scale 양끝 라벨 [1, 5]
  unit?: string;               // number (예: "cm")
  maleOnly?: boolean;          // grooming_self
  noPrefId?: string;           // 이 값이면 절대질문 불가 ("상관없음" 선택지 id)
}

export type AnswerValue = number | string | string[];
export type SurveyResponses = Record<string, AnswerValue>;
