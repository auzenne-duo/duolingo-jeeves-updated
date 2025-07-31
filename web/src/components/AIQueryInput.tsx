import * as React from "react";
import { TextInput } from "web-ui/juicy";

import { queryAI } from "api/jeeves";

interface Props {
  className?: string;
  onQueryResult?: (result: string) => void;
  source: "issue_discovery" | "time_series_analyzer";
}

const AIQueryInput = ({ className, onQueryResult, source }: Props) => {
  const [input, setInput] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);

  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && input.trim() && !isLoading) {
      e.preventDefault();
      setIsLoading(true);

      try {
        const result = await queryAI(input.trim(), source);
        onQueryResult?.(result.response);
        setInput(""); // Clear input after successful query
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("AI query failed:", error);
        // Could add error handling UI here
      } finally {
        setIsLoading(false);
      }
    }

    // Prevent triggering global shortcuts
    e.stopPropagation();
  };

  return (
    <TextInput
      className={className}
      onChange={e => setInput(e.target.value)}
      onKeyDown={handleKeyDown}
      placeholder={
        isLoading ? "Querying AI..." : "Ask AI to generate search query"
      }
      type="text"
      value={input}
    />
  );
};

export default AIQueryInput;
