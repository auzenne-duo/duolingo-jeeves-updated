resource "aws_sns_topic" "jeeves-beta-feedback" {
  name = "jeeves-beta-feedback"

  # The aws_sns_topic.jeeves-beta-feedback is being controlled here and in prod, causing conflicts in management.
  # This is a temporary fix to manage the drift of the dev environment, a separate PR should be created to fix this
  # by changing the dev aws_sns_topic.jeeves-beta-feedback resource to a data source.
  tags = {
    pd-rotation = "snow"
  }
}
