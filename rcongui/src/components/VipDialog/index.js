import React, { useEffect, useState } from "react";
import {
  Button,
  ButtonGroup,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  TextField,
} from "@material-ui/core";

import Autocomplete from "@material-ui/lab/Autocomplete";

import { DateTimePicker, MuiPickersUtilsProvider } from "@material-ui/pickers";
import MomentUtils from "@date-io/moment";
import moment from "moment";
import { PlayerVipSummary } from "./PlayerVipSummary";
import { ForwardCheckBox } from "../commonComponent";

// this array could probably be moved to a config file
const vipButtons = [[48, "hours"], [3, "days"], [7, "days"], [30, "days"], [60, "days"], [0, "Indefinite"]];

const VipTimeButtons = ({
  amount,
  unit,
  expirationTimestamp,
  setExpirationTimestamp,
}) => {
  const adjustTimestamp = (amount, unit) => {
    setExpirationTimestamp(
      moment(expirationTimestamp).add(amount, unit).format()
    );
  };

  const setTimestamp = (amount, unit) => {
    setExpirationTimestamp(moment().add(amount, unit).format());
  };

  // if expiration datetime is jan 1 3000, it's indefinite
  const indefiniateDatetime = "3000-01-01T00:00:00+00:00";
  // if unit is "Indefinite", return a button with the datetime "3000-01-01T00:00:00+00:00
  if (unit === "Indefinite") {
    // return one button with indefiniate datetime
    return (
      <Grid item xs={12}>
        <ButtonGroup variant="contained">
          <Button type="primary" onClick={() => setExpirationTimestamp(moment(indefiniateDatetime))}>
            = {unit}
          </Button>
        </ButtonGroup>
      </Grid>
    );
  }
  else {
    return (
      <Grid item xs={12}>
        <ButtonGroup variant="contained">
          <Button type="primary" onClick={() => setTimestamp(amount, unit)}>
            = {amount} {unit}
          </Button>
          <Button type="primary" onClick={() => adjustTimestamp(amount, unit)}>
            + {amount} {unit}
          </Button>
          <Button type="primary" onClick={() => adjustTimestamp(-amount, unit)}>
            - {amount} {unit}
          </Button>
        </ButtonGroup>
      </Grid>
    );
  }
};

function nameOf(playerObj) {
  if (playerObj) {
    const names = playerObj.get("names");
    if (names.size === 0) {
      return "";
    }
    return playerObj.get("names").get(0).get("name");
  }
}

export function VipExpirationDialog(props) {
  const { open, vips, onDeleteVip, handleClose, handleConfirm , consoleAdmins} = props;
  const [expirationTimestamp, setExpirationTimestamp] = useState();
  const [isVip, setIsVip] = useState(false);
  const [forward, setForward] = useState(false);
  const [oldNote, setOldNote] = useState("");
  const [note, setNote] = useState();
  const [noteType, setNoteType] = useState("");
  const [noteSponsor, setNoteSponsor] = useState("");
  const [noteSuffix, setNoteSuffix] = useState("");

  /* open is either a boolean or the passed in player Map */
  useEffect(() => {
    if (!(typeof open === "boolean") && open) {
      setIsVip(!!vips.get(open.get("steam_id_64")));
      if (open.get("vip_expiration")) {
        setExpirationTimestamp(open.get("vip_expiration"));
      }
      else {
        setExpirationTimestamp();
      }
      // try getting the name from the vip prop
      // todo: test this!!!
      const steamid = open.get("steam_id_64");
      const vip = vips.get(steamid);
      // todo: unpack the existing note into component parts if possible
      setOldNote(vip || "<Not VIP>");
      setNote(vip || nameOf(open));
      setNoteType("");
      setNoteSponsor("");
      setNoteSuffix("");
    }
  }, [open, vips]);

  // update note when noteType, noteSponsor or noteSuffix changes
  useEffect(() => {
    updateNote();
  }, [noteType, noteSponsor, noteSuffix]);
  
  return (
    <Dialog open={open} aria-labelledby="form-dialog-title">
      <DialogTitle id="form-dialog-title">
        Add / Remove / Update VIP Expiration Date
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item>
            <ForwardCheckBox
              bool={forward}
              onChange={() => setForward(!forward)}
            />
          </Grid>
          <Grid item>
            <PlayerVipSummary player={open} isVip={isVip} note={oldNote} />
          </Grid>
          <Grid item container spacing={2}>
            {vipButtons.map(([amount, unit]) => (
              <VipTimeButtons
                key={unit+amount} // fix the key warning
                amount={amount}
                unit={unit}
                expirationTimestamp={expirationTimestamp}
                setExpirationTimestamp={setExpirationTimestamp}
              />
            ))}
          </Grid>
          <Grid item xs={12}>
            <MuiPickersUtilsProvider utils={MomentUtils}>
              <DateTimePicker
                label="New VIP Expiration"
                value={expirationTimestamp}
                onChange={(value) => {
                  setExpirationTimestamp(value.format());
                }}
                format="YYYY/MM/DD HH:mm"
                maxDate={moment("3000-01-01T00:00:00+00:00")}
              />
            </MuiPickersUtilsProvider>
          </Grid>
          <Grid item xs={6}>
            <TextField label="Name" disabled value={nameOf(open)} />
          </Grid>
          <Grid item xs={6}>
            <Autocomplete
              id="vip-note"
              options={[
                "",
                "HLL Seed VIP",
                "Admin Gifted VIP",
                "Patreon VIP",
                "Admin VIP",
                "Special VIP",
                "Gifted VIP",
              ]}
              getOptionLabel={(option) => option}
              value={noteType}
              onChange={(e, value) => {
                setNoteType(value);
              }}
              renderInput={(params) => (
                <TextField {...params} label="VIP type" />
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              label="Note details"
              value={noteSuffix}
              onChange={(e) => setNoteSuffix(e.target.value)}
            />
          </Grid>
          <Grid item xs={6}>
            <Autocomplete
              id="vip-sponsor"
              options={[""].concat(
                consoleAdmins
                  .valueSeq()
                  .toArray()
                  .sort((a, b) =>
                    a.toLowerCase().localeCompare(b.toLowerCase())
                  )
              )}
              getOptionLabel={(option) => option}
              value={noteSponsor}
              onChange={(e, value) => {
                setNoteSponsor(value);
              }}
              renderInput={(params) => (
                <TextField {...params} label="Sponsor (console admin)" />
              )}
            />
          </Grid>
          {/*
            <Grid item xs={4}>
              <Button
                onClick={() => {
                  updateNote();
                }}
              >
                Use as Note
              </Button>
            </Grid>
          */}
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="New VIP note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        {isVip && (
          <Button
            color="secondary"
            onClick={() => {
              setExpirationTimestamp(moment().format());
              onDeleteVip(open, forward);
              handleClose();
            }}
          >
            Remove VIP
          </Button>
        )}
        <Button
          color="primary"
          onClick={() => {
            handleClose();
          }}
        >
          Cancel
        </Button>
        <Button
          onClick={() => {
            handleConfirm(
              open,
              moment.utc(expirationTimestamp).format("YYYY-MM-DD HH:mm:ssZ"),
              forward,
              note
            );
          }}
          color="primary"
        >
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );

  function updateNote() {
    let strArray = [nameOf(open), noteType, noteSponsor, noteSuffix];
    let str = strArray.reduce(function (acc, element, index) {
      // ignore empty elements
      if (typeof element !== 'string' || element.length < 1) {
        return acc;
      }
      // prepend separator only if accumulator is empty (first element) 
      let separator = (acc.length === 0) ? "" : " - ";
      return acc + separator + element;
    }, ""); // "" is the initial value
    setNote(str);
  }
}
