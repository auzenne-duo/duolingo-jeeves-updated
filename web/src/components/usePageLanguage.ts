import { useParams } from "react-router";

const usePageLanguage = () => {
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  return lang;
};

export default usePageLanguage;
