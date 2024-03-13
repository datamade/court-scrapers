-- noqa: disable=PRS
CREATE TABLE court_case(
  case_number not null primary key,
  filing_date text,
  division text,
  subdivision text,
  case_type text,
  calendar text,
  ad_damnum text,
  court text,
  hash text,
  scraped_at text default CURRENT_TIMESTAMP,
  updated_at text default CURRENT_TIMESTAMP
);
-- noqa: enable=PRS

CREATE TABLE plaintiff(
  case_number text not null,
  plaintiff text,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE defendant(
  case_number text not null,
  defendant text,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE attorney(
  case_number text not null,
  attorney text,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE event(
  case_number text not null,
  date text,
  description text,
  comments text,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE court_call(
	case_number text not null,
	division,
	plaintiff,
	defendant,
	court_date,
	room,
	district,
	sequence,
	time,
	hash,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);
