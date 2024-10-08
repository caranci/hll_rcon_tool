import * as React from "react";
import makeStyles from "@material-ui/core/styles/makeStyles";
import Paper from "@material-ui/core/Paper";
import DraggableList from "./DraggableList";
import { getItems, reorder } from "./helpers";
import {
  get,
  handle_http_errors,
  postData,
  sendAction,
  showResponse,
} from "../../utils/fetchUtils";
import { Button, CircularProgress, Grid, Typography } from "@material-ui/core";
import Chip from "@material-ui/core/Chip";
import Autocomplete from "@material-ui/lab/Autocomplete";
import TextField from "@material-ui/core/TextField";

const MapRotation = ({ classes }) => {
  const [maps, setMaps] = React.useState([]);
  const [currentRotation, setCurrentRotation] = React.useState([]);
  const [rotation, setRotation] = React.useState([]);
  const [mapsToAdd, setMapsToAdd] = React.useState([]);
  const [rotationIsSaving, setRotationIsSaving] = React.useState(false);
  const [voteMapConfig, setVoteMapConfig] = React.useState({});
  const [lastRefresh, setLastRefresh] = React.useState(null);

  const loadToState = (command, showSuccess, stateSetter) => {
    return get(command)
      .then((res) => showResponse(res, command, showSuccess))
      .then((res) => (res.failed === false ? stateSetter(res) : null))
      .catch(handle_http_errors);
  };

  const saveRotation = () => {
    setRotationIsSaving(true);
    return postData(`${process.env.REACT_APP_API_URL}set_maprotation`, {
      map_names: rotation.map((m) => m.id),
    })
      .then((res) => {
        showResponse(res, `set_maprotation`, true);
        setRotationIsSaving(false);
        loadMapRotation();
      })
      .catch((e) => {
        handle_http_errors(e);
        loadMapRotation();
        setRotationIsSaving(false);
      });
  };

  const getVoteMapConfig = () => {
    get("get_votemap_config")
      .then((res) => showResponse(res, "get_votemap_config", false))
      .then((data) => (data.failed ? "" : setVoteMapConfig(data.result)))
      .catch(handle_http_errors);
  };

  const loadMapRotation = () => {
    return loadToState("get_map_rotation", false, (data) => {
      setCurrentRotation(Array.from(data.result));
      setRotation(Array.from(data.result));
    });
  };

  const loadAllMaps = () => {
    return loadToState("get_maps", false, (data) => setMaps(data.result));
  };

  const loadAllData = () => {
    getVoteMapConfig();
    loadMapRotation();
    loadAllMaps();
    setLastRefresh(new Date());
  };

  React.useEffect(() => {
    loadAllData();
    const handle = setInterval(getVoteMapConfig, 10000);

    return () => clearInterval(handle);
  }, []);

  const onDragEnd = ({ destination, source }) => {
    // dropped outside the list
    if (!destination) return;

    const newRotation = reorder(rotation, source.index, destination.index);

    setRotation(newRotation);
  };

  const onRemoveItem = (index) => {
    rotation.splice(index, 1);
    setRotation(Array.from(rotation));
  };

  const hasChanged = React.useMemo(
    () => currentRotation.map((o) => o.id).toString() === rotation.map((o) => o.id).toString(),
    [currentRotation, rotation]
  );

  return (
    <Grid container spacing={2} className={classes.doublePadding}>
      <Grid item xs={12}>
        <Typography variant="caption">Drag and drop to reorder</Typography>
      </Grid>
      <Grid item xs={12}>
        <Button variant="text" onClick={loadAllData}>
          <Typography variant="caption">Refresh</Typography>{" "}
        </Button>
      </Grid>
      <Grid item xs={12}>
        <DraggableList
          items={rotation}
          onDragEnd={onDragEnd}
          onRemove={onRemoveItem}
        />
      </Grid>
      <Grid item xs={12}>
        <Grid container spacing={1} alignItems="stretch">
          <Grid item xs={10}>
            <Autocomplete
              multiple
              disableCloseOnSelect
              options={maps}
              getOptionLabel={(m) => m.pretty_name}
              isOptionEqualToValue={(option, value) => option.id == value.id}
              onChange={(e, v) => setMapsToAdd(v)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="outlined"
                  label="Select maps to add"
                />
              )}
            />
          </Grid>
          <Grid item xs={2}>
            <Button
              fullWidth
              style={{ height: "100%" }}
              variant="outlined"
              onClick={() => {
                setRotation(rotation.concat(mapsToAdd));
              }}
            >
              Add
            </Button>
          </Grid>
        </Grid>
      </Grid>
      <Grid item xs={12}>
        <Button
          color="primary"
          variant="outlined"
          fullWidth
          disabled={hasChanged || rotationIsSaving || voteMapConfig.enabled}
          onClick={saveRotation}
        >
          {rotationIsSaving ? (
            <CircularProgress />
          ) : voteMapConfig.enabled ? (
            "You can't change the rotation while votemap is on"
          ) : (
            "Save rotation"
          )}
        </Button>
      </Grid>
    </Grid>
  );
};

export default MapRotation;
