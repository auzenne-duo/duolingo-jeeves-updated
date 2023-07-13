import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import Modal from "react-modal";
import { Button, TextArea } from "web-ui";

import { sendBetaEmails } from "api/jeeves";
import IconButton from "components/IconButton";
import imageClose from "images/x.svg";
import styles from "styles/EmailBetaModal.scss";

interface Props {
  closeModal: () => void;
  isOpen: boolean;
  spike: JSONAPI.SpikeWord;
}

const EmailBetaModal = ({ closeModal, isOpen, spike }: Props) => {
  const descriptionPlaceholder = "We fixed";
  const maxCharacters = 250;
  const remainingCharactersThreshold = 50;
  const [description, setDescription] = React.useState(descriptionPlaceholder);
  const [submitting, setSubmitting] = React.useState(false);
  const [characterCount, setCharacterCount] = React.useState(
    descriptionPlaceholder.length,
  );

  const queryClient = useQueryClient();

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Do not trigger shortcuts.
    e.stopPropagation();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  const mutation = useMutation(
    () => {
      setSubmitting(true);
      return sendBetaEmails(description, spike.spike_id);
    },
    {
      onError: () => {
        setSubmitting(false);
      },
      onSuccess: () => {
        setSubmitting(false);
        closeModal();
        queryClient.invalidateQueries(["spikes"]);
      },
    },
  );

  return (
    <Modal
      ariaHideApp={false}
      className={styles["modal-content"]}
      isOpen={isOpen}
      onRequestClose={closeModal}
      portalClassName={styles["modal"]}
    >
      <IconButton
        className={styles["btn-close"]}
        icon={imageClose}
        onClick={closeModal}
      />
      <div className={styles.header}>
        <strong>
          This will send an email to beta learners who reported the following
          spike:
        </strong>
      </div>
      <div className={styles["text-block"]}>
        &quot;<strong>{spike.word}</strong>: {spike.summary}&quot;
      </div>
      <div className={styles["text-block"]}>
        <strong>Please describe the bug that was fixed:</strong>
      </div>
      <form
        className={styles.form}
        noValidate={true}
        onKeyDown={handleKeyDown}
        onSubmit={handleSubmit}
      >
        <TextArea
          disabled={submitting}
          maxLength={250}
          onChange={e => {
            setDescription(e.target.value);
            setCharacterCount(e.target.value.length);
          }}
          placeholder="Longer description of issue and what has been fixed (500 char max.)"
          required={true}
          rows={5}
          value={description}
        />
        {maxCharacters - characterCount <= remainingCharactersThreshold && (
          <div className={styles["remaining-characters"]}>
            {maxCharacters - characterCount} characters remaining
          </div>
        )}

        <Button
          color="owl"
          disabled={
            !description.trim() || description.trim() === descriptionPlaceholder
          }
          submitting={submitting}
          type="submit"
          variant="solid"
        >
          Submit
        </Button>
      </form>
    </Modal>
  );
};

export default EmailBetaModal;
