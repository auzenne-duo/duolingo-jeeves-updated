import { transformQuery } from "./elastic";

describe("transformQuery", () => {
  it("handles term searches on area", () => {
    const areas = [
      {
        area_name: "Platform",
        teams: [{ features: ["a", "b", "c"], team_name: "Analytics" }],
      },
    ];
    expect(transformQuery("area:Platform", areas)).toBe(
      "feature:(a OR b OR c)",
    );
  });

  it("handles phrase searches on area", () => {
    const areas = [
      {
        area_name: "Product Quality",
        teams: [
          { features: ["a", "b"], team_name: "Delight" },
          { features: ["c"], team_name: "Service Quality" },
        ],
      },
    ];
    expect(transformQuery('area:"Product Quality"', areas)).toBe(
      "feature:(a OR b OR c)",
    );
  });

  it("handles areas and teams without features", () => {
    const areas = [
      {
        area_name: "Monetization",
        teams: [
          { features: [], team_name: "Artemis" },
          { features: [], team_name: "Midas" },
        ],
      },
      {
        area_name: "Product Quality",
        teams: [{ features: ["a", "b"], team_name: "Delight" }],
      },
    ];
    expect(transformQuery("area:Monetization", areas)).toBe("");
    expect(transformQuery("area:Monetization OR team:Artemis", areas)).toBe("");
    expect(
      transformQuery(
        "area:Monetization OR team:Delight OR team:Artemis OR team:Midas",
        areas,
      ),
    ).toBe("feature:(a OR b)");
  });

  it("handles teams with a single feature", () => {
    const areas = [
      {
        area_name: "Product Quality",
        teams: [{ features: ["a"], team_name: "Service Quality" }],
      },
    ];
    expect(transformQuery('team:"Service Quality"', areas)).toBe("feature:a");
  });

  it("handles features with spaces", () => {
    const areas = [
      {
        area_name: "Product Quality",
        teams: [{ features: ["foo bar", "baz"], team_name: "Service Quality" }],
      },
    ];
    expect(transformQuery('team:"Service Quality"', areas)).toBe(
      "feature:(foo\\ bar OR baz)",
    );
  });

  it("handles nested queries", () => {
    const areas = [
      {
        area_name: "Product Quality",
        teams: [
          { features: ["a", "b"], team_name: "Delight" },
          { features: ["c"], team_name: "Service Quality" },
          { features: ["d", "e"], team_name: "Test Automation" },
        ],
      },
    ];
    expect(
      transformQuery(
        'area:"Product Quality" AND (team:Delight OR team:Service\\ Quality)',
        areas,
      ),
    ).toBe(
      "feature:(a OR b OR c OR d OR e) AND (feature:(a OR b) OR feature:c)",
    );
  });

  it("handles field group syntax", () => {
    const areas = [
      {
        area_name: "Platform",
        teams: [{ features: ["a", "b", "c"], team_name: "Analytics" }],
      },
      {
        area_name: "Product Quality",
        teams: [
          { features: ["d", "e"], team_name: "Delight" },
          { features: ["f"], team_name: "Service Quality" },
        ],
      },
    ];
    expect(transformQuery("area:(Platform)", areas)).toBe(
      "feature:(a OR b OR c)",
    );
    expect(transformQuery("area:(Platform OR Product\\ Quality)", areas)).toBe(
      "feature:(a OR b OR c) OR feature:(d OR e OR f)",
    );
    expect(
      transformQuery(
        "area:(Platform OR Foo OR Bar OR Baz OR Product\\ Quality)",
        areas,
      ),
    ).toBe("feature:(a OR b OR c) OR feature:(d OR e OR f)");
  });
});
