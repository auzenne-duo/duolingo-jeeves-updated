import * as React from "react";

import imagePlatformAndroid from "images/android.svg";
import imagePlatformApple from "images/apple.svg";
import imagePlatformWeb from "images/web.svg";

interface Props {
  className?: string;
  platform: "Android" | "iOS" | "Web";
}

const PlatformIcon = ({ className, platform }: Props) => (
  <img
    alt={platform}
    className={className}
    src={
      platform === "Android"
        ? imagePlatformAndroid
        : platform === "iOS"
        ? imagePlatformApple
        : imagePlatformWeb
    }
    title={platform}
  />
);

export default PlatformIcon;
