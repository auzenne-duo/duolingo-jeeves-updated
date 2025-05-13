import { useParams } from "react-router-dom";

const usePageLanguage = (): JSONAPI.LanguageId => {
  const { lang } = useParams<{ lang?: JSONAPI.LanguageId }>();
  return lang ?? "en";
};

export default usePageLanguage;
