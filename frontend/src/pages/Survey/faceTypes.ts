import type { FaceChoice } from "./types";

// TODO(운영 전 교체): 얼굴상 목록·이미지 미확정(TBD, 에셋 의존).
// 실제 AI생성/실사진 확정 시 교체. 이미지 경로도 실제 에셋으로.
export const FACE_ANY_ID = "any";

export const FACE_TYPES: FaceChoice[] = [
  { id: "type_a", label: "강아지상", image: "/faces/placeholder-a.png" },
  { id: "type_b", label: "고양이상", image: "/faces/placeholder-b.png" },
  { id: "type_c", label: "곰상", image: "/faces/placeholder-c.png" },
  { id: "type_d", label: "여우상", image: "/faces/placeholder-d.png" },
];
