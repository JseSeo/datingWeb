export type {
  Section,
  QuestionType,
  Choice,
  FaceChoice,
  Question,
  SurveyCatalog,
} from "../../lib/types";

export type AnswerValue = number | string | string[];
export type SurveyResponses = Record<string, AnswerValue>;
