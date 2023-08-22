import { useMediaQuery } from "web-ui";

const useIsTablet = () => useMediaQuery("(min-width: 768px)");

export default useIsTablet;
