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

console.log('working-days selftest ok', { yearDays, marchPartial });
