export const assert = {
  isTrue: (value: any, message?: string) => {
    if (!value) {
      throw new Error(message || `Expected true but got ${value}`);
    }
  },

  isFalse: (value: any, message?: string) => {
    if (value) {
      throw new Error(message || `Expected false but got ${value}`);
    }
  },

  equals: (actual: any, expected: any, message?: string) => {
    if (actual !== expected) {
      throw new Error(message || `Expected ${expected} but got ${actual}`);
    }
  },

  notEquals: (actual: any, expected: any, message?: string) => {
    if (actual === expected) {
      throw new Error(message || `Expected values to be different but both were ${actual}`);
    }
  },

  hasProperty: (obj: any, property: string, message?: string) => {
    if (!obj || !(property in obj)) {
      throw new Error(message || `Object does not have property '${property}'`);
    }
  },

  isArray: (value: any, message?: string) => {
    if (!Array.isArray(value)) {
      throw new Error(message || `Expected array but got ${typeof value}`);
    }
  },

  isNotEmpty: (value: any, message?: string) => {
    if (!value || (Array.isArray(value) && value.length === 0) || (typeof value === 'object' && Object.keys(value).length === 0)) {
      throw new Error(message || 'Expected non-empty value');
    }
  },

  includes: (arr: any[], value: any, message?: string) => {
    if (!arr.includes(value)) {
      throw new Error(message || `Array does not include ${value}`);
    }
  },

  statusCode: (actual: number, expected: number, message?: string) => {
    if (actual !== expected) {
      throw new Error(message || `Expected status ${expected} but got ${actual}`);
    }
  },
};
