import * as React from "react";
import { SearchSuggestions } from "web-ui";

import PlatformIcon from "components/PlatformIcon";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import AppStateContext from "contexts/AppStateContext";
import { escapeTerm, unescapeSpaces } from "elastic";
import styles from "styles/SearchInput.scss";

const FIELDS = ["area", "feature", "platform", "team"] as const;

// This pattern matches the following:
// - The start of the string, a whitespace character, or opening parenthesis.
//   These are common indicators that we want to match a new field.
// - The field name followed by a colon.
// - A phrase in double quotes, matching as much characters as possible until
//   the next double quote. Does not currently support escaped double quotes.
// - Or: a term that consists of only word characters and escaped spaces.
const PATTERN = String.raw`(^|[\s(])(${FIELDS.join("|")}):("[^"]*|(?:\w|\\ )*)`;

const PLATFORMS: JSONAPI.Platform[] = ["Android", "iOS", "Web"];

interface ImperativeHandle {
  /** Moves the caret to the given position. */
  setCaret: (index: number) => void;
}

type ListItem = SearchSuggestionsProps["items"][number];

export interface SearchInputChangeEvent extends SearchSuggestionsChangeEvent {
  /**
   * If a list item has been inserted into the query, the caret
   * should be moved to this position for the best user experience.
   */
  suggestedCaret?: number;
}

type SearchInputChangeHandler = (e: SearchInputChangeEvent) => void;

type SearchSuggestionsChangeEvent = Parameters<
  Exclude<SearchSuggestionsProps["onChange"], undefined>
>[0];

type SearchSuggestionsProps = React.ComponentProps<typeof SearchSuggestions>;

type SearchSuggestionsSelectEvent = Parameters<
  Exclude<SearchSuggestionsProps["onSelect"], undefined>
>[0];

interface SubQuery {
  end: number;
  field: typeof FIELDS[number];
  isQuoted: boolean;
  start: number;
  term: string;
}

const alphabeticalSorter = (a: ListItem, b: ListItem) =>
  a.text.localeCompare(b.text);

interface Props
  extends Pick<SearchSuggestionsProps, "className" | "onKeyDown" | "value"> {
  onChange?: SearchInputChangeHandler;
}

const SearchInput = (
  { className, onChange, onKeyDown, value = "" }: Props,
  ref: React.Ref<ImperativeHandle>,
) => {
  const { data: areas = [] } = useFeaturesByTeamAndArea();

  const [{ searchHistory }] = React.useContext(AppStateContext);

  const [matches, setMatches] = React.useState<SubQuery[]>();
  const [selectionStart, setSelectionStart] = React.useState<number>();
  const [selectionEnd, setSelectionEnd] = React.useState<number>();

  const searchRef =
    React.useRef<React.ElementRef<typeof SearchSuggestions>>(null);

  const handleSelect = (e: SearchSuggestionsSelectEvent) => {
    if (subQuery === undefined) {
      onChange?.({ value: e.value.text });
    } else {
      const term = `${escapeTerm(e.value.text, subQuery.isQuoted)}${
        subQuery.isQuoted ? '"' : ""
      }`;
      onChange?.({
        // Suggest for the caret to be moved to the end of the inserted term.
        suggestedCaret:
          subQuery.start + term.length - (subQuery.isQuoted ? 1 : 0),
        value: `${value.slice(0, subQuery.start)}${term}${value.slice(
          subQuery.end + (subQuery.isQuoted ? 1 : 0),
        )}`,
      });
    }
  };

  const measureCaret = () => {
    const searchEl = searchRef.current?.getSearchEl();
    setSelectionStart(searchEl?.selectionStart ?? undefined);
    setSelectionEnd(searchEl?.selectionEnd ?? undefined);
  };

  React.useEffect(() => {
    measureCaret();
    setMatches(
      [...value.matchAll(new RegExp(PATTERN, "g"))].map<SubQuery>(match => {
        const prefix = match[1];
        const field = match[2] as typeof FIELDS[number];
        const isQuoted = match[3].startsWith('"');
        const term = isQuoted ? match[3].slice(1) : match[3];
        const start =
          // Not sure when this can be undefined?
          (match.index ?? 0) +
          prefix.length +
          field.length +
          (isQuoted ? 1 : 0) +
          1;
        const end = start + term.length;
        return {
          end,
          field,
          isQuoted,
          start,
          term,
        };
      }),
    );
  }, [value]);

  React.useImperativeHandle(ref, () => ({
    setCaret: index => {
      searchRef.current?.getSearchEl()?.setSelectionRange(index, index);
      measureCaret();
    },
  }));

  const subQuery = React.useMemo(() => {
    if (selectionStart === undefined || selectionEnd === undefined) {
      return undefined;
    }
    // Loop over all eligible fields and check if the caret or
    // selection is in the term part of that field's query.
    return matches?.find(
      m => selectionStart >= m.start && selectionEnd <= m.end,
    );
  }, [matches, selectionEnd, selectionStart]);

  const items = React.useMemo(() => {
    switch (subQuery?.field) {
      case "area":
        return areas.map(a => ({ text: a.area_name })).sort(alphabeticalSorter);
      case "feature":
        return areas
          .flatMap(a =>
            a.teams.flatMap(t =>
              t.features.map(f => ({
                description: `owned by ${t.team_name}`,
                text: f,
              })),
            ),
          )
          .sort(alphabeticalSorter);
      case "platform":
        return PLATFORMS.map(p => ({
          icon: <PlatformIcon className={styles.icon} platform={p} />,
          text: p,
        }));
      case "team":
        return areas
          .flatMap(a =>
            a.teams.map(t => ({
              description: `in ${a.area_name}`,
              text: t.team_name,
            })),
          )
          .sort(alphabeticalSorter);
      default:
        return searchHistory.map(q => ({ text: q }));
    }
  }, [areas, searchHistory, subQuery?.field]);

  return (
    <SearchSuggestions
      className={className}
      // This number should be large enough to fill the list height
      // on most screens. Otherwise flickering occurs as the number
      // of shown items is reset each time the query changes.
      initialItems={10}
      items={items}
      onChange={onChange}
      onKeyDown={onKeyDown}
      // The new caret is position is only available on the -up variants of these events.
      // When tabbing to the input this also triggers a key up event.
      onKeyUp={measureCaret}
      onMouseUp={measureCaret}
      onSelect={handleSelect}
      query={
        subQuery === undefined
          ? value
          : subQuery.isQuoted
          ? subQuery.term
          : unescapeSpaces(subQuery.term)
      }
      ref={searchRef}
      value={value}
    />
  );
};

export default React.forwardRef(SearchInput);
