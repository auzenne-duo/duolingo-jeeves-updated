import * as React from "react";

import imagePlatformAndroid from "images/android.svg";
import imagePlatformApple from "images/apple.svg";
import imageTwitter from "images/twitter.svg";
import imagePlatformWeb from "images/web.svg";

interface Props {
  className?: string;
  platform: JSONAPI.Platform | "Twitter";
}

const PlatformIcon = ({ className, platform }: Props) => (
  <img
    alt={platform}
    className={className}
    src={
      platform === "Twitter"
        ? imageTwitter
        : platform === "Android"
        ? imagePlatformAndroid
        : platform === "iOS"
        ? imagePlatformApple
        : imagePlatformWeb
    }
    title={platform}
  />
);

export default PlatformIcon;
