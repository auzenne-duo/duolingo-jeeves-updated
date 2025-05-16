import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import track from "../../track";

const useQuery = () => new URLSearchParams(useLocation().search);

const FEATURE_PARAM = "feature";
const ID_PARAM = "id";
const QUICK_FEEDBACK_PARAM = "quick_feedback";

const REQUIRED_PARAMS = [FEATURE_PARAM, ID_PARAM, QUICK_FEEDBACK_PARAM];

const FeedbackPage: React.FC = () => {
  const query = useQuery();
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params: Record<string, string | null> = {};
    for (const key of REQUIRED_PARAMS) {
      params[key] = query.get(key);
    }
    const missing = REQUIRED_PARAMS.filter(key => !params[key]);
    if (missing.length > 0) {
      setError(`Missing required parameter(s): ${missing.join(", ")}`);
      setStatus("error");
      return;
    }

    setStatus("loading");
    track("jeeves_generic_feedback", {
      feature: params[FEATURE_PARAM] as string,
      id: params[ID_PARAM] as string,
      quick_feedback: params[QUICK_FEEDBACK_PARAM] as string,
    }).then(() => setStatus("success"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === "loading") {
    return <div>Sending feedback...</div>;
  }
  if (status === "error") {
    return (
      <div
        style={{
          backgroundColor: "#FFEBE6",
          borderRadius: "3px",
          color: "#DE350B",
          marginTop: "20px",
          padding: "10px",
        }}
      >
        Error: {error}
      </div>
    );
  }
  if (status === "success") {
    return (
      <div
        style={{
          backgroundColor: "#E3FCEF",
          borderRadius: "3px",
          color: "#006644",
          marginTop: "20px",
          padding: "10px",
        }}
      >
        Thank you! Your feedback was received and tracked successfully.
      </div>
    );
  }
  return null;
};

export default FeedbackPage;
