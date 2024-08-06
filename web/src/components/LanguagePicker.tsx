import * as React from "react";
import { Select } from "web-ui";

const LANGUAGES: Record<JSONAPI.LanguageId, string> = {
  all: "ALL",
  de: "German",
  en: "English",
  es: "Spanish",
  fr: "French",
  hi: "Hindi",
  it: "Italian",
  ja: "Japanese",
  pt: "Portuguese",
  ru: "Russian",
  xx: "Other",
  zh: "Chinese",
};

interface Props {
  className?: string;
  onChange: (value: JSONAPI.LanguageId) => void;
  value: JSONAPI.LanguageId;
}

const LanguagePicker = ({ className, onChange, value }: Props) => (
  <Select
    className={className}
    onChange={e => onChange(e.target.value as JSONAPI.LanguageId)}
    options={Object.entries(LANGUAGES)
      .map(([k, v]) => ({ text: v, value: k }))
      .sort((a, b) => a.text.localeCompare(b.text))}
    text={`${LANGUAGES[value]} tickets`}
    type="secondary"
    value={value}
  />
);

export default LanguagePicker;
