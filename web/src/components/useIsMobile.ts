import { useMediaQuery } from "web-ui";

const useIsMobile = () => useMediaQuery("not screen and (min-width: 768px)");

export default useIsMobile;
