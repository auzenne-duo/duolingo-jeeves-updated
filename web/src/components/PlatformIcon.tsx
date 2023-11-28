import * as React from "react";

import imagePlatformAndroid from "images/android.svg";
import imagePlatformApple from "images/apple.svg";
import imageReddit from "images/reddit.svg";
import imageTwitter from "images/twitter.svg";
import imagePlatformWeb from "images/web.svg";

interface Props {
  className?: string;
  platform: JSONAPI.Platform | "Reddit" | "Twitter";
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
          : platform === "Reddit"
            ? imageReddit
            : platform === "Twitter"
              ? imageTwitter
              : imagePlatformWeb
    }
    title={platform}
  />
);

export default PlatformIcon;
