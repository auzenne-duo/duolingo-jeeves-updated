import { useLocation } from "react-router-dom";

const useSearchParams = () => new URLSearchParams(useLocation().search);

export default useSearchParams;
