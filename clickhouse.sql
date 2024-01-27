CREATE TABLE `cs_history`
(
    `dateTime`      DateTime DEFAULT NOW(),
    `date`          Date DEFAULT toDate(NOW()),
    `url`           String,
    `data`          String
)
    ENGINE MergeTree() PARTITION BY toYYYYMM(date) ORDER BY (date) SETTINGS index_granularity=8192;
