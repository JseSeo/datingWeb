import { useEffect, useState } from "react";
import {
  listPendingVerifications,
  reviewVerification,
  fetchVerificationImage,
} from "../../lib/api";
import type { AdminVerificationOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

function Card({
  item,
  onReviewed,
}: {
  item: AdminVerificationOut;
  onReviewed: (id: number) => void;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [imageUrl]);

  async function showImage() {
    setImageError("");
    try {
      const url = await fetchVerificationImage(item.id);
      setImageUrl(url);
    } catch {
      setImageError("이미지를 불러오지 못했어요.");
    }
  }

  async function review(action: "approve" | "reject") {
    setBusy(true);
    try {
      await reviewVerification(item.id, action);
      onReviewed(item.id);
    } catch {
      setImageError("처리에 실패했어요. 다시 시도해주세요.");
      setBusy(false);
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.name}>{item.name}</div>
      <div className={styles.university}>{item.university}</div>
      {imageUrl ? (
        <img className={styles.image} src={imageUrl} alt={`${item.name} 학생증`} />
      ) : (
        <Button onClick={showImage}>학생증 보기</Button>
      )}
      {imageError && <p className={styles.error}>{imageError}</p>}
      <div className={styles.actions}>
        <Button onClick={() => review("approve")} disabled={busy}>
          승인
        </Button>
        <Button onClick={() => review("reject")} disabled={busy}>
          반려
        </Button>
      </div>
    </div>
  );
}

export default function Admin() {
  const [items, setItems] = useState<AdminVerificationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listPendingVerifications()
      .then((data) => {
        if (active) setItems(data);
      })
      .catch(() => {
        if (active) setError("목록을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function removeItem(id: number) {
    setItems((prev) => prev.filter((v) => v.id !== id));
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>학생증 심사</h1>
      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && items.length === 0 && <p>심사 대기 없음</p>}
      {items.map((item) => (
        <Card key={item.id} item={item} onReviewed={removeItem} />
      ))}
    </div>
  );
}
