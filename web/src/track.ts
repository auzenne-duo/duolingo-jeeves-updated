import * as excess from "web-excess";

excess.init();
excess.setDebug(process.env.NODE_ENV === "development");

const jwt = document.cookie
  .split("; ")
  .find(row => row.startsWith("jwt_token="))
  ?.split("=")[1];

const userId = jwt ? JSON.parse(atob(jwt.split(".")[1])).sub : undefined;

if (userId !== undefined) {
  excess.identify(userId);
}

interface TrackingEvents {
  jeeves_active_user: undefined;
}

const track = <T extends keyof TrackingEvents>(
  event: T,
  props?: TrackingEvents[T],
) =>
  new Promise<void>(resolve => {
    excess.track(event, props, () => resolve);
  });

export default track;
