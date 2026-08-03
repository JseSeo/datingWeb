import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { submitReport, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import type { ReportType } from "../../lib/types";
import styles from "./Report.module.css";

export default function Report() {
  const navigate = useNavigate();
  const [type, setType] = useState<ReportType | "">("");
  const [targetName, setTargetName] = useState("");
  const [targetUniversity, setTargetUniversity] = useState("");
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<"" | "sending" | "sent" | "error">("");
  const [error, setError] = useState("");

  const isReport = type === "report";

  function selectType(next: ReportType) {
    setType(next);
    setStatus("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!type) return;
    setStatus("sending");
    setError("");
    try {
      await submitReport({
        type,
        target_name: isReport ? targetName.trim() : null,
        target_university: isReport ? targetUniversity.trim() : null,
        reason,
      });
      setStatus("sent");
      setType("");
      setTargetName("");
      setTargetUniversity("");
      setReason("");
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiError ? err.message : "접수에 실패했습니다");
    }
  }

  return (
    <div className={styles.wrap}>
      <button type="button" className={styles.back} aria-label="마이페이지로 돌아가기"
        onClick={() => navigate("/mypage")}>‹ 마이페이지로 돌아가기</button>
      <h1 className={styles.title}>신고 &amp; 건의</h1>
      <form onSubmit={handleSubmit}>
        <fieldset className={styles.type}>
          <legend>유형</legend>
          <label>
            <input type="radio" name="type" checked={type === "report"}
              onChange={() => selectType("report")} /> 신고
          </label>
          <label>
            <input type="radio" name="type" checked={type === "suggestion"}
              onChange={() => selectType("suggestion")} /> 건의
          </label>
        </fieldset>
        <p className={styles.hint}>작성 내용과 작성자 정보는 관리자에게 전달됩니다</p>

        {isReport && (
          <>
            <Input id="target-name" label="신고 대상 이름" value={targetName}
              maxLength={100}
              onChange={(e) => setTargetName(e.target.value)} />
            <Input id="target-university" label="신고 대상 학교" value={targetUniversity}
              maxLength={100}
              onChange={(e) => setTargetUniversity(e.target.value)} />
            <p className={styles.hint}>
              학과·학번·인스타 아이디 등 대상을 특정할 수 있는 정보를 본문에 함께 적어주세요
            </p>
          </>
        )}

        <label htmlFor="reason" className={styles.label}>내용</label>
        <textarea id="reason" className={styles.textarea} value={reason}
          maxLength={2000}
          placeholder={isReport ? "신고 사유를 적어주세요" : "건의 내용을 적어주세요"}
          onChange={(e) => setReason(e.target.value)} />

        {status === "sent" && <p className={styles.ok}>접수되었습니다</p>}
        {status === "error" && <p className={styles.error}>{error}</p>}

        <Button type="submit" disabled={!type || status === "sending"}>
          {status === "sending" ? "전송 중..." : "제출"}
        </Button>
      </form>
    </div>
  );
}
