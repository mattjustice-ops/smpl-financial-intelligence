import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const wd = require('../public/shared/working-days.js');

const year = 2027;
const yearDays = wd.yearWorkingDays(year, []);
assert.equal(wd.monthWorkingDays(year, 2, []), 20, 'February 2027 has 20 weekdays');
assert.equal(wd.monthWorkingDays(year, 3, []), 23, 'March 2027 has 23 weekdays');
assert.equal(wd.daysOnPayroll(year, 3, '2027-03-20', []), 8, 'A 20 March start works 8 weekdays');
assert.equal(wd.daysOnPayroll(year, 3, null, []), 23);
assert.equal(wd.daysOnPayroll(year, 2, '2027-03-01', []), 0);

let sum = 0;
for (let month = 1; month <= 12; month++) sum += wd.monthWorkingDays(year, month, []);
assert.equal(sum, yearDays);

const salary = 120000;
assert.equal(wd.accrue(salary, yearDays, yearDays, 0, 0), salary);
const marchPartial = wd.accrue(salary, yearDays, 8, 0, 0);
assert.ok(Math.abs(marchPartial - salary * 8 / yearDays) < 1e-6);

const merit = wd.splitMerit(year, 4, null, '2027-04-15', []);
assert.equal(merit.before + merit.after, wd.monthWorkingDays(year, 4, []));
assert.ok(merit.before > 0 && merit.after > 0);
const raised = wd.accrue(salary, yearDays, merit.before, merit.after, 0.03);
const flat = wd.accrue(salary, yearDays, merit.before + merit.after, 0, 0);
assert.ok(raised > flat);

const holiday = ['2027-07-05'];
assert.equal(new Date(2027, 6, 5).getDay(), 1, '5 July 2027 is a Monday');
assert.equal(wd.monthWorkingDays(year, 7, holiday), wd.monthWorkingDays(year, 7, []) - 1);
assert.equal(wd.yearWorkingDays(year, holiday), yearDays - 1);

const csv = wd.holidayTemplateCsv([2027], [{ year: 2027, name: 'Memorial Day', date: '2027-05-31' }]);
const parsed = wd.parseHolidayCsv(csv);
assert.deepEqual(parsed.errors, []);
assert.equal(parsed.rows.length, 1);
assert.equal(parsed.rows[0].date, '2027-05-31');
assert.ok(parsed.years.includes(2027));
const merged = wd.mergeHolidayRows(
  [{ year: 2026, name: 'Christmas Day', date: '2026-12-25' }],
  parsed,
);
assert.equal(merged.length, 2);
assert.deepEqual(wd.holidayDatesForYear(merged, 2027), ['2027-05-31']);
const bad = wd.parseHolidayCsv('Year,Holiday,Date\n2027,July 4,07/04/2027\n');
assert.equal(bad.rows.length, 0);
assert.equal(bad.errors.length, 1);

console.log('working-days selftest ok', { yearDays, marchPartial });
