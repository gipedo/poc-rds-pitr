#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "@aws-cdk/core";
import { PocRdsPitrStack } from "../lib/poc-rds-pitr-stack";
require("dotenv").config();

const app = new cdk.App();
new PocRdsPitrStack(app, "PocRdsPitrStack", {
  // @ts-ignore
  trustedDbIngress: process.env.TRUSTED_INGRESS_DB_CIDR,
});
