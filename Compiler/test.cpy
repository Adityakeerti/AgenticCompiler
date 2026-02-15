// ===========================
//  CPY Language Test Program
// ===========================

// --- Variable declarations ---
let x = 10;
let y = 20;
let sum = x + y;
print(sum);

// --- String support ---
let name = "CPY Language";
print(name);

// --- Arithmetic ---
let result = (x * y) + 5 - 3;
print(result);

// --- If / Else ---
if (x < y) {
    print("x is less than y");
} else {
    print("x is not less than y");
}

// --- While loop ---
let counter = 0;
while (counter < 5) {
    print(counter);
    counter = counter + 1;
}

// --- For loop ---
for (let i = 0; i < 5; i = i + 1) {
    print(i);
}

// --- Nested if ---
let score = 85;
if (score >= 90) {
    print("Grade: A");
} else {
    if (score >= 80) {
        print("Grade: B");
    } else {
        print("Grade: C");
    }
}

// --- String concatenation ---
let greeting = "Hello, " + name + "!";
print(greeting);

// --- Boolean / comparison ---
let isEqual = (x == y);
print(isEqual);

// --- Division ---
let division = y / x;
print(division);

// --- Char literals ---
let ch = 'A';
print(ch);
let ch2 = 'z';
print(ch2);

// --- Arrays ---
let nums = [10, 20, 30, 40, 50];
print(nums);
print(nums[0]);
print(nums[4]);

// --- Array with mixed types ---
let mixed = [1, "hello", 'X'];
print(mixed);
print(mixed[1]);
print(mixed[2]);

// --- Array mutation ---
nums[2] = 999;
print(nums);
print(nums[2]);

// --- Array with expressions ---
let arr = [x + y, x * 2, y - 5];
print(arr);

// --- Loop over array using index ---
let colors = ["red", "green", "blue"];
for (let j = 0; j < 3; j = j + 1) {
    print(colors[j]);
}

// --- Empty array ---
let empty = [];
print(empty);
