import _ from "lodash";

import * as Fuse from "fuse.js";

export function TestNode(suite_name, file, test_id) {
  return JSON.stringify({
    _type: "test",
    suite: suite_name,
    file: file,
    id: test_id
  });
}

function TestsNodes(testList, suite_name, file) {
  var childrens = [];

  for (var test of testList) {
    let value = TestNode(suite_name, file, test.id);
    let node = {
      label: test.test_name,
      value: value,
      children: [],
      className: `balto-test-${test.outcome}`
    };
    childrens.push(node);
  }

  return childrens;
}

function ChildrentByFile(testList, suite_name) {
  var nodes = [];

  var x = _.groupBy(testList, test => test.file);
  for (var [file, testsByFile] of Object.entries(x)) {
    let childrens = TestsNodes(testsByFile, suite_name, file);
    let value = JSON.stringify({ _type: "file", suite: suite_name, id: file });
    let children = { label: file, value: value, children: childrens };
    nodes.push(children);
  }
  return nodes;
}

export function treeFromTests(testsList) {
  /*let testsList = Object.values(tests);*/

  let nodes = [];

  var x = _.groupBy(testsList, test => test.suite_name);
  for (var [suite_name, testsBySuite] of Object.entries(x)) {
    let childrens = ChildrentByFile(testsBySuite, suite_name);
    let value = JSON.stringify({ _type: "suite", id: suite_name });
    let node = { label: suite_name, value: value, children: childrens };
    nodes.push(node);
  }

  return nodes;
}

export function filterTest(testsList, filter) {
  if (filter === "") {
    return testsList;
  }

  if (testsList.length == 0) {
    return [];
  }

  var fuseOptions = {
    shouldSort: true,
    tokenize: true,
    findAllMatches: true,
    threshold: 0.4,
    location: 0,
    distance: 100,
    maxPatternLength: 32,
    minMatchCharLength: 1,
    keys: ["_type", "test_name", "id"]
  };

  var fuse = new Fuse(testsList, fuseOptions);
  var filtered = fuse.search(filter);
  return filtered;
}