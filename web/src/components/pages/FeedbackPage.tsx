import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Button, TextArea, TextInput } from "web-ui/juicy";

import track from "../../track";

const useQuery = () => new URLSearchParams(useLocation().search);

const FEATURE_PARAM = "feature";
const ID_PARAM = "id";
const QUICK_FEEDBACK_PARAM = "quick_feedback";

const REQUIRED_PARAMS = [FEATURE_PARAM, ID_PARAM, QUICK_FEEDBACK_PARAM];

const FeedbackCard: React.FC<{
  background: string;
  children: React.ReactNode;
  color: string;
  style?: React.CSSProperties;
}> = ({ background, children, color, style }) => (
  <div
    className="web-ui-card"
    style={{
      background,
      borderRadius: 8,
      boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
      color,
      fontSize: 18,
      marginTop: 40,
      maxWidth: 420,
      padding: 32,
      ...style,
    }}
  >
    {children}
  </div>
);

const FeedbackPage: React.FC = () => {
  const query = useQuery();
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error" | "long_feedback"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [longFeedback, setLongFeedback] = useState("");
  const [params, setParams] = useState<Record<string, string | null>>({});

  useEffect(() => {
    const collectedParams: Record<string, string | null> = {};
    for (const key of REQUIRED_PARAMS) {
      collectedParams[key] = query.get(key);
    }
    setParams(collectedParams);
    const missing = REQUIRED_PARAMS.filter(key => !collectedParams[key]);
    if (missing.length > 0) {
      setError(`Missing required parameter(s): ${missing.join(", ")}`);
      setStatus("error");
      return;
    }

    setStatus("loading");
    track("jeeves_generic_feedback", {
      feature: collectedParams[FEATURE_PARAM] as string,
      id: collectedParams[ID_PARAM] as string,
      long_feedback: undefined,
      quick_feedback: collectedParams[QUICK_FEEDBACK_PARAM] as string,
    })
      .then(() => setStatus("long_feedback"))
      .catch(() => {
        setError("Failed to send feedback");
        setStatus("error");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLongFeedbackSubmit = async (
    e: React.FormEvent<HTMLFormElement>,
  ) => {
    e.preventDefault();
    setStatus("loading");
    const totalFeedback = name ? `${name}: ${longFeedback}` : longFeedback;
    try {
      await track("jeeves_generic_feedback", {
        feature: params[FEATURE_PARAM] as string,
        id: params[ID_PARAM] as string,
        long_feedback: totalFeedback,
        quick_feedback: params[QUICK_FEEDBACK_PARAM] as string,
      });
      setStatus("success");
    } catch {
      setError("Failed to send long feedback");
      setStatus("error");
    }
  };

  if (status === "loading") {
    return <div>Sending feedback...</div>;
  }
  if (status === "error") {
    return (
      <FeedbackCard background="#FFEBE6" color="#DE350B">
        Error: {error}
      </FeedbackCard>
    );
  }
  if (status === "success") {
    return (
      <FeedbackCard
        background="#E3FCEF"
        color="#006644"
        style={{ fontSize: 20 }}
      >
        Thank you! Your feedback was received and tracked successfully.
      </FeedbackCard>
    );
  }
  if (status === "long_feedback") {
    return (
      <FeedbackCard background="#E3FCEF" color="#006644">
        <div style={{ fontSize: 20, marginBottom: 16 }}>
          Thank you! Your feedback was submitted.
          <br />
          <div style={{ height: 12 }} />
          If you&apos;d like, you can add your name and provide more details
          below (optional).
          <div style={{ color: "#333", fontSize: 15, marginTop: 8 }}>
            You can close this page if you have no more feedback.
          </div>
        </div>
        <form onSubmit={handleLongFeedbackSubmit} style={{ marginTop: 20 }}>
          <div style={{ marginBottom: 16 }}>
            <TextInput
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onChange={(e: any) => setName(e.target.value)}
              placeholder="Your name (optional)"
              state="enabled"
              type="text"
              value={name}
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <TextArea
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              onChange={(e: any) => setLongFeedback(e.target.value)}
              placeholder="Additional feedback (optional)"
              rows={4}
              state="enabled"
              value={longFeedback}
            />
          </div>
          <Button type="submit">Submit</Button>
        </form>
      </FeedbackCard>
    );
  }
  return null;
};

export default FeedbackPage;
