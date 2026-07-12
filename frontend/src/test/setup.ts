import "@testing-library/jest-dom";

if (typeof URL.createObjectURL === "undefined") {
  Object.defineProperty(URL, "createObjectURL", {
    value: () => "",
    writable: true,
  });
}
