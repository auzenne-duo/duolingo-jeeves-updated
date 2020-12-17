import * as React from "react";

import imagePlatformAndroid from "images/android.svg";
import imagePlatformApple from "images/apple.svg";
import imagePlatformWeb from "images/web.svg";
import { formatPlatform } from "util";

interface Props {
  className?: string;
  platform: "android" | "ios" | "web";
}

const PlatformIcon: React.FC<Props> = ({ className, platform }) => (
  <img
    alt={formatPlatform(platform)}
    className={className}
    src={
      platform === "android"
        ? imagePlatformAndroid
        : platform === "ios"
        ? imagePlatformApple
        : imagePlatformWeb
    }
    title={formatPlatform(platform)}
  />
);

export default PlatformIcon;
