-- noqa: disable=PRS
CREATE TABLE court_case(
  case_number not null primary key,
  filing_date text not null,
  division text not null,
  subdivision text,
  case_type text not null,
  calendar text not null,
  ad_damnum text not null,
  court text not null,
  hash text,
  scraped_at text default CURRENT_TIMESTAMP,
  updated_at text default CURRENT_TIMESTAMP
	);
-- noqa: enable=PRS

CREATE TABLE plaintiff(
  case_number text not null,
  plaintiff text not null,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE defendant(
  case_number text not null,
  defendant text not null,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE attorney(
  case_number text not null,
  attorney text not null,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE event(
  case_number text not null,
  date text not null,
  description text,
  comments text,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);

CREATE TABLE court_call(
	case_number text not null,
	division,
	plaintiff,
	defendant,
	calendar,
	court_date,
	room,
	district,
	sequence,
	time,
	call_type,
	hash,
  FOREIGN KEY(case_number) REFERENCES court_case(case_number)
);
