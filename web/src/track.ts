import * as excess from "web-excess";

import { getLoggedInUserId } from "api/user";

excess.init();
excess.setDebug(process.env.NODE_ENV === "development");

try {
  excess.identify(`${getLoggedInUserId()}`);
} catch (ex) {
  // Logged out
}

interface TrackingEvents {
  jeeves_active_user: {
    is_admin: boolean;
    language?: string;
    page?: string;
    user_agent: string;
    utc_offset: number;
  };
  jeeves_search: {
    id: string;
    is_admin: boolean;
    jeeves_answer?: string;
    language?: string;
    link?: string;
    num_results: number;
    page?: string;
    query: string;
    query_time_ms: number;
    query_type: string;
    user_agent: string;
    utc_offset: number;
  };
  shake_to_report_feedback: {
    feature?: string;
    number_suggested_features: number;
    report_type: "jeeves";
    selected_suggested_feature: boolean;
    slack_channel?: string;
  };
}

const track = <T extends keyof TrackingEvents>(
  event: T,
  props?: TrackingEvents[T],
) =>
  new Promise<void>(resolve => {
    excess.track(event, props, () => resolve);
  });

export default track;
